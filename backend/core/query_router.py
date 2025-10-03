import asyncio
import hashlib
import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .settings_manager import get_settings_manager

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the system can handle."""

    SPECIFIC_IMAGE_SEARCH = "specific_image_search"
    SHOW_ME_PATTERN = "show_me_pattern"
    ALL_IMAGES = "all_images"
    GENERAL_IMAGE_PATTERN = "general_image_pattern"
    AI_TEXT_RESPONSE = "ai_text_response"


class QueryRouter:
    """Service for routing and parsing different types of user queries."""

    # Class constants for illustration query patterns
    ILLUSTRATION_SHOW_ALL_PATTERNS = [
        "illustrations",
        "illustrations done",
        "illustrations done?",
        "illustrations created",
        "illustrations created?",
        "done",
        "done?",
        "created",
        "created?",
    ]

    def __init__(self):
        # Define patterns and keywords
        self.image_keywords = [
            "image",
            "images",
            "illustration",
            "illustrations",
            "drawing",
            "drawings",
            "art",
            "pic",
            "pics",
            "picture",
            "pictures",
        ]

        self.specific_image_keywords = [
            "images of",
            "image of",
            "drawings of",
            "drawing of",
            "pics of",
            "pic of",
            "pictures of",
            "picture of",
            "illustrations of",
            "illustration of",
            "art about",
            "art of",
        ]

        self.show_me_patterns = ["show me", "show", "find", "get", "display"]

        self.image_indicators = [
            "images",
            "image",
            "illustrations",
            "illustration",
            "drawings",
            "drawing",
            "art",
            "pics",
            "pictures",
        ]

        self.ignore_words = {
            "show",
            "me",
            "tell",
            "describe",
            "explain",
            "get",
            "give",  # Added "give" to ignore words
            "find",
            "display",
            "see",
            "view",
            "look",
            "at",
            "the",
            "a",
            "an",
            "some",
            "any",
            "all",
            "your",
            "of",
            "about",
            "please",
            "describe",
            "for",
            "more",  # Added "more" to ignore words
            "details",  # Added "details" to ignore words
            # Question words that should be filtered out when extracting search terms
            "what",
            "are",
            "is",
            "do",
            "does",
            "did",
            "have",
            "has",
            "had",
            "you",
            "they",
            "we",
            "i",
            "can",
            "could",
            "would",
            "should",
            "will",
            "shall",
            "may",
            "might",
            "been",
            "being",
            "done",
            "made",
            "created",
            "different",
            "various",
            "which",
            "that",
            "this",
            "these",
            "those",
            "there",
            "here",
            "when",
            "where",
            "why",
            "how",
        }

        self.all_image_phrases = [
            "show me all illustrations",
            "show all illustrations",
            "show me your illustrations",
            "show me all your art",
            "show me all images",
            "show me images",
            "show your art",
            "all images",
            "all illustrations",
            "all art",
            "show me everything",
            "show me illustrations",
            "show me art",
            "show me pictures",
            "show me drawings",
            "find illustrations",
            "find images",
            "find art",
            "find pictures",
            "find drawings",
            "get illustrations",
            "get images",
            "get art",
            "get pictures",
            "get drawings",
            "display illustrations",
            "display images",
            "display art",
            "display pictures",
            "display drawings",
            # Question patterns that are asking to see all illustrations
            "what illustrations",
            "what illustrations have you done",
            "what illustrations you have done",
            "what different illustrations",
            "what different illustrations have you done",
            "what different illustrations you have done",
            "what are different illustrations",
            "what are different illustrations have you done",
            "what are different illustrations you have done",
            "illustrations",
            "illustrations have you done",
            "illustrations you have done",
            "different illustrations",
            "different illustrations have you done",
            "different illustrations you have done",
            # "Show me" patterns asking for variety/styles (show all)
            "show me different art styles you have done",
            "show me different art styles you've done",
            "show me different art styles",
            "show me art styles",
            "show me styles",
            "different art styles",
            "art styles",
        ]

    @staticmethod
    def _clean_word(word: str) -> str:
        """Strip leading/trailing punctuation and quotes from a word."""
        if not word:
            return word
        strip_chars = "\"'()[]{}.,!?;:"
        return word.strip(strip_chars)

    def route_query(self, question: str) -> Tuple[QueryType, Optional[str]]:
        """
        Route a query to determine its type and extract search terms.

        Args:
            question: The user's question (should be lowercased and stripped)

        Returns:
            Tuple of (QueryType, search_term or None)
        """
        # Check if smart routing is enabled via feature flag
        settings_manager = get_settings_manager()
        if not settings_manager.is_feature_enabled("enable_smart_routing"):
            # Fall back to simple routing - default to AI text response
            logger.debug("Smart routing disabled via feature flag, using simple routing")
            return QueryType.AI_TEXT_RESPONSE, None

        # Route to specific image search
        search_term = self._check_specific_image_search(question)
        if search_term:
            return QueryType.SPECIFIC_IMAGE_SEARCH, search_term

        # Route to show all images BEFORE checking show me patterns
        # This prevents "show me images" from being incorrectly parsed as "show me 's'"
        if self._check_all_images_pattern(question):
            return QueryType.ALL_IMAGES, "all"

        # Route to "show me X" patterns
        search_term = self._check_show_me_pattern(question)
        if search_term:
            return QueryType.SHOW_ME_PATTERN, search_term

        # Route to general image patterns
        search_term = self._check_general_image_pattern(question)
        if search_term:
            return QueryType.GENERAL_IMAGE_PATTERN, search_term

        # Default to AI text response
        return QueryType.AI_TEXT_RESPONSE, None

    def _check_specific_image_search(self, question: str) -> Optional[str]:
        """Check for specific image search patterns like 'images of X'."""
        for trigger in self.specific_image_keywords:
            if trigger in question:
                search_term = question.split(trigger, 1)[1].strip()
                if search_term:
                    logger.info(f"Specific image search detected: '{search_term}'")
                    return search_term
        return None

    def _check_show_me_pattern(self, question: str) -> Optional[str]:
        """Check for 'show me X images/illustrations' patterns."""
        for show_pattern in self.show_me_patterns:
            if question.startswith(show_pattern):
                remaining_text = question[len(show_pattern) :].strip()

                # Check if it contains image indicators
                found_image_indicator = False
                for img_indicator in self.image_indicators:
                    if img_indicator in remaining_text:
                        found_image_indicator = True
                        search_term = self._extract_search_term_from_show_pattern(remaining_text, img_indicator)
                        if search_term:
                            logger.info(f"Show me pattern detected: '{search_term}'")
                            return search_term

                # If we found an image indicator but no valid search term (only ignore words),
                # return None to let it fall through to other patterns
                if found_image_indicator:
                    return None
        return None

    def _extract_search_term_from_show_pattern(self, remaining_text: str, img_indicator: str) -> Optional[str]:
        """Extract search term from 'show me X images' pattern."""
        # Check if the remaining text is exactly just the image indicator
        # This handles cases like "show me images" or "find illustrations" where we want to show all
        if remaining_text.strip() == img_indicator:
            return None

        # Split into words to handle whole word matching
        words = [self._clean_word(w) for w in remaining_text.split()]

        # Find the image indicator word and remove it, keeping other words
        search_words = []
        for word in words:
            if word != img_indicator:
                search_words.append(word)

        if not search_words:
            return None

        # Filter out common words that are not part of the search term
        filtered_words = [word for word in search_words if word and word not in self.ignore_words]
        search_term = " ".join(filtered_words).strip()

        # If the search term is empty after filtering ignore words, return None
        # This handles cases like "show me the images" where "the" gets filtered out
        # but preserves cases like "find illustrations" where there are no ignore words to filter
        if not search_term:
            return None

        # If the search term consists only of image indicators, return None
        if search_term in self.image_indicators:
            return None

        return search_term

    def _check_all_images_pattern(self, question: str) -> bool:
        """Check for patterns that request all images."""
        # First check exact match
        if question in self.all_image_phrases:
            return True

        # Then check with ignore words filtered out
        words = question.split()
        filtered_words = [word for word in words if word not in self.ignore_words]
        filtered_question = " ".join(filtered_words)

        if filtered_question in self.all_image_phrases:
            return True

        # Special case: if the filtered question is just punctuation or empty after filtering,
        # but contains illustration keywords, treat it as "show all"
        if filtered_question.strip() in self.ILLUSTRATION_SHOW_ALL_PATTERNS:
            return True

        return False

    def _check_general_image_pattern(self, question: str) -> Optional[str]:
        """Check for general patterns like 'X images' or 'X art'."""
        original_words = question.split()
        words = [self._clean_word(w) for w in original_words]
        for img_indicator in self.image_indicators:
            if img_indicator in words:
                # Get the index of the image indicator
                idx = words.index(img_indicator)

                # Extract words before and after the image indicator
                words_before = words[:idx]
                words_after = words[idx + 1 :]

                # Filter out ignore words
                search_terms_before = [w for w in words_before if w and w not in self.ignore_words]
                search_terms_after = [w for w in words_after if w and w not in self.ignore_words]

                # Combine the search terms
                search_term = " ".join(search_terms_before + search_terms_after).strip()

                if search_term:
                    logger.info(f"General image pattern detected: '{search_term}'")
                    return search_term

        return None

    def is_image_query(self, question: str) -> bool:
        """Check if a query is asking for images/illustrations."""
        query_type, _ = self.route_query(question)
        return query_type != QueryType.AI_TEXT_RESPONSE

    # === ENHANCED ROUTING METHODS WITH CONFIGURATION SUPPORT ===

    async def route_query_with_confidence(
        self, question: str, chat_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Route query with confidence scoring and configurable fallback strategies.

        Returns:
            Dict containing routing decision with confidence score and metadata
        """
        start_time = time.time()
        routing_settings = get_settings_manager().get_routing_settings()

        try:
            # Perform smart routing with confidence analysis
            routing_result = await self._smart_route_with_confidence(question, chat_history, routing_settings)

            # Check if confidence meets threshold
            if routing_result["confidence"] < routing_settings.confidence_threshold:
                logger.info(
                    f"Low confidence ({routing_result['confidence']:.2f}) for query: '{question[:50]}...', applying fallback"
                )
                routing_result = await self._apply_fallback_strategy(question, chat_history, routing_settings)

            # Add performance metadata
            processing_time = time.time() - start_time
            routing_result["processing_time"] = processing_time
            routing_result["settings_applied"] = True

            return routing_result

        except Exception as e:
            logger.error(f"Error in enhanced query routing: {e}")
            return await self._emergency_fallback(question, chat_history)

    async def _smart_route_with_confidence(
        self, question: str, chat_history: Optional[List[Dict]], settings
    ) -> Dict[str, Any]:
        """Perform smart routing with confidence analysis."""

        # Analyze query intent
        intent_analysis = self._analyze_query_intent(question)

        # Determine query type using existing logic
        query_type, search_term = self.route_query(question)

        # Calculate confidence based on multiple factors
        confidence_score = self._calculate_confidence_score(question, query_type, search_term, intent_analysis)

        return {
            "strategy": "smart_routing",
            "query_type": query_type.value,
            "search_term": search_term,
            "confidence": confidence_score,
            "intent": intent_analysis.get("intent", "unknown"),
            "topics": intent_analysis.get("topics", []),
            "enable_caching": settings.enable_caching,
            "cache_ttl": settings.cache_ttl_seconds,
            "parallel_processing": settings.enable_parallel_processing,
        }

    def _analyze_query_intent(self, question: str) -> Dict[str, Any]:
        """Analyze query intent and extract topics."""

        # Simple intent analysis based on question patterns
        intent = "question"
        topics = []

        # Detect question types
        if any(word in question.lower() for word in ["what", "how", "why", "when", "where", "who"]):
            intent = "question"
        elif any(word in question.lower() for word in ["show", "find", "display", "get"]):
            intent = "retrieval"
        elif any(word in question.lower() for word in ["explain", "tell me about", "describe"]):
            intent = "explanation"
        else:
            intent = "general"

        # Extract topics based on keywords
        if any(word in question.lower() for word in ["code", "programming", "development", "technical"]):
            topics.append("technical")
        if any(word in question.lower() for word in ["experience", "work", "job", "career"]):
            topics.append("experience")
        if any(word in question.lower() for word in ["skills", "knowledge", "expertise"]):
            topics.append("skills")
        if any(word in question.lower() for word in ["about", "personal", "background"]):
            topics.append("personal")
        if any(word in question.lower() for word in self.image_keywords):
            topics.append("creative")

        return {
            "intent": intent,
            "topics": topics,
            "complexity": len(question.split()),  # Simple complexity metric
        }

    def _calculate_confidence_score(
        self, question: str, query_type: QueryType, search_term: Optional[str], intent_analysis: Dict
    ) -> float:
        """Calculate confidence score for routing decision."""

        confidence = 0.5  # Base confidence

        # Boost confidence for clear image queries
        if query_type != QueryType.AI_TEXT_RESPONSE:
            confidence += 0.3

            # Additional boost if search term is clear
            if search_term and len(search_term.strip()) > 2:
                confidence += 0.2

        # Boost confidence for questions with clear intent
        if intent_analysis.get("intent") in ["question", "retrieval", "explanation"]:
            confidence += 0.1

        # Boost confidence for queries with identified topics
        if intent_analysis.get("topics"):
            confidence += 0.1 * min(len(intent_analysis["topics"]), 2)  # Max 0.2 boost

        # Penalize very short or very long queries
        word_count = len(question.split())
        if word_count < 2:
            confidence -= 0.2
        elif word_count > 50:
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    async def _apply_fallback_strategy(
        self, question: str, chat_history: Optional[List[Dict]], settings
    ) -> Dict[str, Any]:
        """Apply configured fallback strategy."""

        strategy = settings.fallback_strategy
        logger.info(f"Applying fallback strategy: {strategy}")

        if strategy == "comprehensive_search":
            return await self._comprehensive_search_fallback(question, chat_history)
        elif strategy == "semantic_similarity":
            return await self._semantic_similarity_fallback(question, chat_history)
        elif strategy == "keyword_matching":
            return await self._keyword_matching_fallback(question, chat_history)
        elif strategy == "default_response":
            return await self._default_response_fallback(question, chat_history)
        else:
            # Unknown strategy, use comprehensive search as default
            return await self._comprehensive_search_fallback(question, chat_history)

    async def _comprehensive_search_fallback(self, question: str, chat_history: Optional[List[Dict]]) -> Dict[str, Any]:
        """Comprehensive search across all content types."""
        return {
            "strategy": "comprehensive_search",
            "query_type": "comprehensive",
            "search_all_types": True,
            "use_semantic_similarity": True,
            "use_keyword_matching": True,
            "confidence": 0.5,
            "fallback_applied": True,
        }

    async def _semantic_similarity_fallback(self, question: str, chat_history: Optional[List[Dict]]) -> Dict[str, Any]:
        """Focus on semantic similarity matching."""
        return {
            "strategy": "semantic_similarity",
            "query_type": "semantic",
            "search_method": "semantic_only",
            "similarity_threshold": 0.6,
            "confidence": 0.6,
            "fallback_applied": True,
        }

    async def _keyword_matching_fallback(self, question: str, chat_history: Optional[List[Dict]]) -> Dict[str, Any]:
        """Focus on keyword-based matching."""
        # Honor SearchRetrievalSettings.enable_fuzzy_matching for keyword fallback behavior
        try:
            from .settings_manager import get_settings_manager

            sr_settings = get_settings_manager().get_search_retrieval_settings()
            fuzzy_enabled = bool(getattr(sr_settings, "enable_fuzzy_matching", True))
        except Exception:
            fuzzy_enabled = True

        return {
            "strategy": "keyword_matching",
            "query_type": "keyword",
            "search_method": "keyword_only",
            "use_fuzzy_matching": fuzzy_enabled,
            "confidence": 0.4,
            "fallback_applied": True,
        }

    async def _default_response_fallback(self, question: str, chat_history: Optional[List[Dict]]) -> Dict[str, Any]:
        """Default response strategy."""
        return {
            "strategy": "default_response",
            "query_type": "default",
            "use_default_context": True,
            "confidence": 0.3,
            "fallback_applied": True,
        }

    async def _emergency_fallback(self, question: str, chat_history: Optional[List[Dict]]) -> Dict[str, Any]:
        """Emergency fallback when all routing fails."""
        logger.error(f"Emergency fallback activated for query: '{question[:50]}...'")
        return {
            "strategy": "emergency_fallback",
            "query_type": "emergency",
            "search_all_types": True,
            "use_comprehensive_search": True,
            "confidence": 0.2,
            "error_occurred": True,
        }

    async def route_query_with_retries(
        self, question: str, chat_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Route query with configurable retry logic."""
        routing_settings = get_settings_manager().get_routing_settings()
        max_retries = routing_settings.max_retries

        for attempt in range(max_retries + 1):
            try:
                result = await self.route_query_with_confidence(question, chat_history)

                # Validate result quality
                if self._is_result_acceptable(result, routing_settings):
                    if attempt > 0:
                        logger.info(f"Query routing succeeded on attempt {attempt + 1}")
                    return result

                if attempt < max_retries:
                    logger.info(f"Routing attempt {attempt + 1} produced low-quality result, retrying...")
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue

                # Final attempt - return what we have
                logger.warning(f"All {max_retries + 1} routing attempts completed, returning best available result")
                return result

            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Routing attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue

                # Final attempt failed - use emergency fallback
                logger.error(f"All routing attempts failed: {e}")
                return await self._emergency_fallback(question, chat_history)

    def _is_result_acceptable(self, result: Dict[str, Any], settings) -> bool:
        """Validate if routing result meets quality standards."""

        # Emergency fallback results are always considered acceptable (check first)
        if result.get("error_occurred", False):
            return True

        # Check if confidence meets threshold (for non-fallback strategies)
        if not result.get("fallback_applied", False):
            if result.get("confidence", 0) < settings.confidence_threshold:
                return False

        # Check if we have sufficient routing information
        if not result.get("query_type") and not result.get("strategy"):
            return False

        return True

    def log_routing_performance(
        self, question: str, routing_decision: Dict[str, Any], processing_time: float, attempt_count: int = 1
    ):
        """Log routing performance metrics for analytics."""
        try:
            performance_data = {
                "query_hash": hashlib.md5(question.encode()).hexdigest()[:8],
                "routing_strategy": routing_decision.get("strategy"),
                "query_type": routing_decision.get("query_type"),
                "confidence": routing_decision.get("confidence"),
                "processing_time_ms": processing_time * 1000,
                "attempt_count": attempt_count,
                "fallback_applied": routing_decision.get("fallback_applied", False),
                "error_occurred": routing_decision.get("error_occurred", False),
                "settings_applied": routing_decision.get("settings_applied", False),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Log basic performance info
            logger.info(
                f"Routing performance: {performance_data['routing_strategy']} "
                f"({performance_data['confidence']:.2f} confidence, "
                f"{performance_data['processing_time_ms']:.1f}ms)"
            )

            # TODO: Integrate with query analytics system if available
            # self.query_logger.log_routing_performance(performance_data)

        except Exception as e:
            logger.warning(f"Failed to log routing performance: {e}")
