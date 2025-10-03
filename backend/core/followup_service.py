import hashlib
import logging
import random
import threading
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text

from .db_session import get_db_session_sync
from .settings_manager import get_settings_manager  # kept for backward-compat in tests

# Note: Settings are fetched via this service's own cache; direct manager import remains for patching in tests
from .settings_schemas import FollowUpSettings

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for generating smart follow-up question suggestions with configurable settings."""

    def __init__(self) -> None:
        # Fallback question pools for different categories (kept for backward compatibility)
        self.question_pools = {
            "technical": [
                "What technologies do you work with?",
                "Tell me about your development philosophy?",
                "Show me your coding projects",
                "What frameworks do you prefer?",
                "How do you approach problem solving?",
            ],
            "personal": [
                "Tell me about your experience",
                "What's your background?",
                "How can I contact Nick?",
                "What motivates you?",
                "Tell me about your journey",
            ],
            "creative": [
                "Show me your illustrations",
                "What inspires your artwork?",
                "Tell me about your creative process",
                "Show me your design work",
                "What art styles do you enjoy?",
            ],
        }

        # Default static questions (fallback)
        self.default_questions: Tuple[str, ...] = (
            "Show me your illustrations",
            "Tell me about your experience",
            "What inspires your artwork?",
            "What technologies do you work with?",
            "What's your development philosophy?",
            "How can I contact Nick?",
        )

        # Track current position for sequential ordering
        self.current_index: int = 0
        # Thread lock for concurrent access protection
        self._lock = threading.Lock()
        # Cache settings to avoid frequent database calls
        self._cached_settings: Optional[FollowUpSettings] = None
        self._settings_cache_timestamp: float = 0
        # Cache categories to avoid frequent database calls
        self._cached_categories: Optional[List[Dict]] = None
        self._categories_cache_timestamp: float = 0

    @property
    def questions(self) -> Tuple[str, ...]:
        """Return immutable default questions tuple for backward compatibility and testing."""
        return self.default_questions

    def clear_cache(self) -> None:
        """Clear the settings and categories cache to force reload on next request."""
        with self._lock:
            self._cached_settings = None
            self._settings_cache_timestamp = 0
            self._cached_categories = None
            self._categories_cache_timestamp = 0
            logger.info("FollowUpService: Cache cleared, will reload on next request")

    def _get_settings(self) -> FollowUpSettings:
        """Get current settings with caching."""
        import time

        current_time = time.time()
        # Cache settings for 60 seconds to reduce database calls
        if self._cached_settings is None or current_time - self._settings_cache_timestamp > 60:

            try:
                sm = get_settings_manager()
                self._cached_settings = sm.get_followup_settings()
                self._settings_cache_timestamp = current_time
                logger.info(f"FollowUpService: Loaded follow-up settings: {self._cached_settings.to_dict()}")
            except Exception as e:
                logger.warning(f"Failed to load follow-up settings, using defaults: {e}")
                self._cached_settings = FollowUpSettings()
                self._settings_cache_timestamp = current_time

        return self._cached_settings

    def _get_active_categories(self) -> List[Dict]:
        """Get active categories from database with caching, scoped to current tenant."""
        import os
        import time

        current_time = time.time()
        # Cache categories for 60 seconds to reduce database calls
        if self._cached_categories is None or current_time - self._categories_cache_timestamp > 60:
            try:
                with get_db_session_sync() as session:
                    if session is None:
                        raise RuntimeError("No DB session")

                    # Get tenant_id from current session context or use default
                    fallback_tid = os.getenv("DEFAULT_TENANT_ID") or "00000000-0000-0000-0000-000000000001"

                    # Query with explicit tenant filter (defense-in-depth with RLS)
                    rows = session.execute(
                        text(
                            "SELECT id, name, display_name, description, icon, sort_order "
                            "FROM followup_categories "
                            "WHERE is_active = true "
                            "AND tenant_id = COALESCE("
                            "NULLIF(current_setting('app.tenant_id', true), '')::uuid, "
                            "CAST(:fallback_tid AS uuid)) "
                            "ORDER BY sort_order, name"
                        ),
                        {"fallback_tid": fallback_tid},
                    ).fetchall()
                    self._cached_categories = [
                        {
                            "id": r[0],
                            "name": r[1],
                            "display_name": r[2],
                            "description": r[3],
                            "icon": r[4],
                            "sort_order": int(r[5] or 0),
                            "is_active": True,
                        }
                        for r in rows
                    ]
                    self._categories_cache_timestamp = current_time
                    logger.info(
                        f"FollowUpService: Loaded {len(self._cached_categories)} active categories for tenant context"
                    )
            except Exception as e:
                logger.warning(f"Failed to load categories, using fallback: {e}")
                # Create fallback category structure from hardcoded pools
                self._cached_categories = [
                    {"name": "technical", "display_name": "Technical", "is_active": True},
                    {"name": "personal", "display_name": "Personal", "is_active": True},
                    {"name": "creative", "display_name": "Creative", "is_active": True},
                ]
                self._categories_cache_timestamp = current_time

        return self._cached_categories

    def _build_question_pool(self, settings: FollowUpSettings) -> List[str]:
        """Build question pool based on settings and active categories, using normalized questions table."""
        questions = []

        # Get active categories from database
        active_categories = self._get_active_categories()

        # Sort categories by sort_order and then by name to ensure consistent ordering
        active_categories = sorted(active_categories, key=lambda c: (c.get("sort_order", 0), c.get("name", "")))

        # Get questions from normalized database structure (primary source)
        try:
            for category in active_categories:
                category_id = category.get("id")
                category_name = category.get("name", "")

                # Check if this category type should be included based on settings
                should_include = (
                    (category_name == "technical" and settings.include_technical)
                    or (category_name == "personal" and settings.include_personal)
                    or (category_name == "creative" and settings.include_creative)
                    or (
                        category_name not in ["technical", "personal", "creative"]
                    )  # Include custom categories by default
                )

                if should_include and category_id:
                    # Get active questions for this category from normalized table, scoped to tenant
                    with get_db_session_sync() as session:
                        if session is None:
                            raise RuntimeError("No DB session")

                        # Get tenant_id from session context or use default
                        import os

                        fallback_tid = os.getenv("DEFAULT_TENANT_ID") or "00000000-0000-0000-0000-000000000001"

                        # Query with explicit tenant filter (defense-in-depth with RLS)
                        qrows = session.execute(
                            text(
                                "SELECT id, question_text, sort_order "
                                "FROM followup_questions "
                                "WHERE category_id = :cid AND is_active = true "
                                "AND tenant_id = COALESCE("
                                "NULLIF(current_setting('app.tenant_id', true), '')::uuid, "
                                "CAST(:fallback_tid AS uuid)) "
                                "ORDER BY sort_order, id"
                            ),
                            {"cid": category_id, "fallback_tid": fallback_tid},
                        ).fetchall()
                        category_questions = [
                            {"id": qr[0], "question_text": qr[1], "sort_order": int(qr[2] or 0), "is_active": True}
                            for qr in qrows
                        ]
                    # Sort questions by sort_order and id to ensure consistent ordering within category
                    category_questions = sorted(
                        category_questions, key=lambda q: (q.get("sort_order", 0), q.get("id", 0))
                    )
                    # Extract just the question text
                    questions.extend([q["question_text"] for q in category_questions])
                    logger.debug(
                        f"Loaded {len(category_questions)} questions from category '{category_name}' (ID: {category_id})"
                    )
        except Exception as e:
            logger.warning(f"Failed to load questions from normalized structure: {e}")

        # Secondary fallback: legacy custom_questions from settings
        if not questions and settings.custom_questions:
            logger.info("No database questions found, falling back to legacy custom_questions from settings")
            # Use already sorted active_categories for consistent ordering
            for category in active_categories:
                category_name = category.get("name", "")

                # Check if this category type should be included based on settings
                if (
                    (category_name == "technical" and settings.include_technical)
                    or (category_name == "personal" and settings.include_personal)
                    or (category_name == "creative" and settings.include_creative)
                    or (
                        category_name not in ["technical", "personal", "creative"]
                    )  # Include custom categories by default
                ):
                    if category_name in settings.custom_questions:
                        questions.extend(settings.custom_questions[category_name])

        # Final fallback: hardcoded question pools (backward compatibility only)
        if not questions:
            logger.warning(
                "No database or legacy questions found, falling back to hardcoded question pools (consider running migration)"
            )
            # Use already sorted active_categories for consistent ordering
            for category in active_categories:
                category_name = category.get("name", "")

                # Check if this category type should be included and exists in hardcoded pools
                if category_name in self.question_pools:
                    if (
                        (category_name == "technical" and settings.include_technical)
                        or (category_name == "personal" and settings.include_personal)
                        or (category_name == "creative" and settings.include_creative)
                    ):
                        questions.extend(self.question_pools[category_name])

        # If still no questions available, use defaults
        if not questions:
            questions = list(self.default_questions)

        logger.debug(
            f"FollowUpService: Built question pool with {len(questions)} questions from {len(active_categories)} categories"
        )
        return questions

    def _generate_static_questions(self, settings: FollowUpSettings) -> List[str]:
        """Generate questions using static/sequential method."""
        questions_pool = self._build_question_pool(settings)

        if not questions_pool:
            logger.warning("FollowUpService: No questions available, returning empty list")
            return []

        # Return sequential questions with wrap-around
        with self._lock:
            selected_questions = []
            for i in range(settings.max_questions):
                question_index = (self.current_index + i) % len(questions_pool)
                selected_questions.append(questions_pool[question_index])

            # Advance index for next call
            self.current_index = (self.current_index + settings.max_questions) % len(questions_pool)
            logger.debug(f"FollowUpService static: selected {len(selected_questions)} questions")

        return selected_questions

    def _generate_dynamic_questions(
        self, settings: FollowUpSettings, user_question: str, ai_response: str
    ) -> List[str]:
        """Generate questions using dynamic method based on context."""
        # For now, this is similar to static but could be enhanced with AI analysis
        # TODO: Implement smart context-based question selection
        questions_pool = self._build_question_pool(settings)

        if not questions_pool:
            return []

        # Simple implementation: prefer questions that aren't too similar to current query
        # This could be enhanced with semantic similarity in the future
        # Use thread-safe deterministic randomness based on stable hash
        stable_hash = int(hashlib.sha256(user_question.lower().encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(stable_hash)

        selected = rng.sample(questions_pool, min(settings.max_questions, len(questions_pool)))

        logger.debug(f"FollowUpService dynamic: selected {len(selected)} questions")
        return selected

    def _generate_contextual_questions(
        self,
        settings: FollowUpSettings,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> List[str]:
        """Generate questions using contextual analysis (most advanced)."""
        # For now, this is the same as dynamic but could be enhanced with conversation analysis
        # TODO: Implement conversation-aware question generation
        return self._generate_dynamic_questions(settings, user_question, ai_response)

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """
        Generate follow-up questions based on current settings and context.

        Args:
            user_question: The user's original question.
            ai_response: The AI's response.
            conversation_history: Previous conversation for context.

        Returns:
            A list of follow-up questions.
        """
        try:
            # Respect legacy feature flag gate (mapped to FollowUpSettings.enabled by SettingsManager)
            try:
                settings_manager = get_settings_manager()
                if not settings_manager.is_feature_enabled("enable_followup_questions"):
                    logger.debug("Follow-up questions disabled via feature flag")
                    return []
            except Exception:
                # Proceed if settings manager unavailable
                pass

            settings = self._get_settings()

            # If disabled, return no questions
            if not settings.enabled:
                logger.debug("Follow-up questions disabled in settings")
                return []

            # Generate based on service type
            if settings.service_type == "static":
                return self._generate_static_questions(settings)
            elif settings.service_type == "dynamic":
                return self._generate_dynamic_questions(settings, user_question, ai_response)
            elif settings.service_type == "contextual":
                return self._generate_contextual_questions(settings, user_question, ai_response, conversation_history)
            else:
                logger.warning(f"Unknown service type: {settings.service_type}, using static")
                return self._generate_static_questions(settings)

        except Exception as e:
            logger.error(f"Error generating follow-ups: {e}", exc_info=True)
            # Fallback to simple static behavior
            return [self.default_questions[self.current_index % len(self.default_questions)]]

    def reload_settings(self) -> None:
        """Force reload of settings from database."""
        self._cached_settings = None
        self._settings_cache_timestamp = 0
        logger.info("Follow-up settings cache cleared, will reload on next request")

    def reload_categories(self) -> None:
        """Force reload of categories from database."""
        self._cached_categories = None
        self._categories_cache_timestamp = 0
        logger.info("Follow-up categories cache cleared, will reload on next request")

    def get_available_categories(self) -> List[Dict]:
        """Get all available categories for admin UI."""
        return self._get_active_categories()
