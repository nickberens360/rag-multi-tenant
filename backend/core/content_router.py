"""
Content router component for intelligent query routing and content type detection.

This module provides focused functionality for:
- Query intent analysis and content type detection
- Smart routing based on query patterns
- Adaptive search strategy selection
- Content type hint extraction
- Metadata filter extraction from natural language queries

NOTE: As of Phase 2 taxonomy refactor, this module uses database-driven taxonomy
from tenant_taxonomy table instead of file-based taxonomy_loader.
"""

import logging
import re
from typing import Dict, List, Optional

from langchain.docstore.document import Document

from ..models.filter_models import MetadataFilter, RetrievalFilters
from .config_v2 import AppConfig
from .semantic_searcher import SemanticSearcher

logger = logging.getLogger(__name__)


def get_tenant_taxonomy(tenant_id: str) -> Dict[str, Dict]:
    """
    Load taxonomy from tenant_taxonomy table (unified source).

    Replaces legacy taxonomy_loader.get_topic_taxonomy() with database query.
    This is the new unified approach for Phase 2+ taxonomy refactor.

    Args:
        tenant_id: Tenant UUID

    Returns:
        Dictionary mapping category keys to {label, synonyms, regex} data.
        Returns empty dict if database is unavailable or query fails.

    Example return value:
        {
            "documentation": {
                "label": "Technical Documentation",
                "synonyms": ["docs", "api", "reference"],
                "regex": ["\\bdocs\\b", "\\bapi\\b"]
            },
            "tutorial": {
                "label": "Tutorials & How-Tos",
                "synonyms": ["how-to", "guide"],
                "regex": ["\\btutorial\\b", "\\bhow-to\\b"]
            }
        }
    """
    from .db_session import get_db_session_sync
    from sqlalchemy import text

    taxonomy = {}

    try:
        with get_db_session_sync() as session:
            if session is None:
                # Database not available (multi-tenant disabled or connection failed)
                logger.warning(
                    "Database session unavailable. Cannot load taxonomy. "
                    "Tenant should bootstrap taxonomy via POST /api/admin/taxonomy/bootstrap"
                )
                return {}

            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})

            rows = session.execute(
                text(
                    """
                    SELECT key, label, synonyms, regex
                    FROM tenant_taxonomy
                    WHERE tenant_id = :tid AND active = true
                    """
                ),
                {"tid": tenant_id},
            ).fetchall()

            for row in rows:
                taxonomy[row[0]] = {
                    "label": row[1],
                    "synonyms": row[2] if row[2] else [],
                    "regex": row[3] if row[3] else [],
                }

            if taxonomy:
                logger.debug(f"Loaded {len(taxonomy)} taxonomy entries from database for tenant {tenant_id[:8]}...")
            else:
                logger.warning(
                    f"No taxonomy found for tenant {tenant_id[:8]}. "
                    "Bootstrap taxonomy via: POST /{tenant}/api/admin/taxonomy/bootstrap?template_key=software"
                )

    except Exception as e:
        logger.error(f"Failed to load taxonomy for tenant {tenant_id}: {e}")

    return taxonomy


class ContentRouter:
    """Handles intelligent query routing and content type detection."""

    def __init__(self, semantic_searcher: SemanticSearcher):
        self.semantic_searcher = semantic_searcher

    def detect_metadata_filters(self, query: str) -> RetrievalFilters:
        """
        Detect metadata filter requests from natural language queries.

        This method extracts metadata filtering intent from queries like:
        - "show me technical documents" -> content_type:technical (soft)
        - "only technical content" -> content_type:technical:strict (strict)
        - "python tutorials" -> tags:python (soft)
        - "strictly python code" -> tags:python:strict (strict)

        Args:
            query: User query text

        Returns:
            RetrievalFilters object with detected filters
        """
        query_lower = query.lower().strip()
        filters = RetrievalFilters()

        # Pattern 1: Detect strict intent keywords
        strict_keywords = ["only", "strictly", "exclusively", "must be", "just"]
        is_strict = any(keyword in query_lower for keyword in strict_keywords)

        # Pattern 2: Detect content type filters
        content_type_patterns = {
            "technical": [r"\btechnical\b", r"\bcode\b", r"\bapi\b", r"\bdocumentation\b"],
            "experience": [r"\bexperience\b", r"\bwork history\b", r"\bresume\b", r"\bjobs?\b"],
            "about": [r"\babout\b", r"\bbackground\b", r"\bbio\b", r"\bpersonal\b"],
            "creative": [r"\bcreative\b", r"\bart\b", r"\bdesign\b", r"\billustration\b"],
            "project": [r"\bprojects?\b", r"\bportfolio\b", r"\bbuilt\b", r"\bcreated\b"],
        }

        for content_type, patterns in content_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    filters.content_type = MetadataFilter(
                        field="effective_content_type", value=content_type, strict=is_strict
                    )
                    logger.debug(f"Detected content_type filter: {content_type} ({'strict' if is_strict else 'soft'})")
                    break
            if filters.content_type:
                break

        # Pattern 3: Detect tag filters (programming languages, technologies)
        tag_patterns = {
            "python": [r"\bpython\b"],
            "javascript": [r"\bjavascript\b", r"\bjs\b"],
            "typescript": [r"\btypescript\b", r"\bts\b"],
            "react": [r"\breact\b"],
            "vue": [r"\bvue\b", r"\bvuejs\b"],
            "fastapi": [r"\bfastapi\b"],
            "docker": [r"\bdocker\b"],
            "kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
            "aws": [r"\baws\b", r"\bamazon web services\b"],
            "gcp": [r"\bgcp\b", r"\bgoogle cloud\b"],
        }

        for tag, patterns in tag_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    filters.tags.append(
                        MetadataFilter(field="effective_tags", value=tag, strict=is_strict, boost_weight=0.3)
                    )
                    logger.debug(f"Detected tag filter: {tag} ({'strict' if is_strict else 'soft'})")
                    break

        if filters.has_filters():
            logger.info(
                f"Detected {len(filters.get_strict_filters())} strict filters, "
                f"{len(filters.get_soft_filters())} soft filters from query"
            )

        return filters

    def detect_content_types(self, query: str, tenant_id: Optional[str] = None) -> List[str]:
        """
        Detect content types based on query patterns using tenant taxonomy.

        Args:
            query: User query text
            tenant_id: Optional tenant UUID. If provided, uses database taxonomy.
                      If not provided, falls back to legacy file-based taxonomy.

        Returns:
            List of detected content type hints
        """
        query_lower = query.lower().strip()
        hints: List[str] = []

        # 1) Try taxonomy-driven detection
        # Use database taxonomy if tenant_id provided, otherwise legacy
        if tenant_id:
            taxonomy_dict = get_tenant_taxonomy(tenant_id)
            cats = taxonomy_dict  # Already in {key: {label, synonyms, regex}} format
        else:
            # Legacy fallback
            legacy_taxonomy = get_topic_taxonomy()
            if legacy_taxonomy and isinstance(legacy_taxonomy.get("categories"), dict):
                cats = legacy_taxonomy["categories"]
            else:
                cats = None

        if cats:

            for cat_name, cfg in cats.items():
                matched = False

                # Build effective regex patterns from synonyms and explicit regex overrides
                patterns: List[re.Pattern] = []
                synonyms = [s for s in (cfg.get("synonyms") or []) if isinstance(s, str) and s.strip()]
                if synonyms:
                    try:
                        escaped = [re.escape(s.strip()) for s in synonyms]
                        # Word-boundary group for all synonyms, case-insensitive
                        syn_pattern = re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)
                        patterns.append(syn_pattern)
                    except re.error:
                        # If building the grouped pattern fails, fall back to per-synonym tests
                        for s in synonyms:
                            try:
                                patterns.append(re.compile(r"\b" + re.escape(s.strip()) + r"\b", re.IGNORECASE))
                            except re.error:
                                continue

                for pattern in cfg.get("regex") or []:
                    if not isinstance(pattern, str):
                        continue
                    try:
                        patterns.append(re.compile(pattern, re.IGNORECASE))
                    except re.error:
                        continue

                # Try regex-based matching first
                for pat in patterns:
                    try:
                        if pat.search(query_lower):
                            matched = True
                            break
                    except re.error:
                        continue

                # Fallback: simple substring search on synonyms (legacy behavior)
                if not matched and synonyms:
                    for word in synonyms:
                        if word and word.lower() in query_lower:
                            matched = True
                            break

                if matched:
                    hints.append(cat_name)

            # Special case retained for inspiration/artistic implying 'about'
            if ("inspiration" in query_lower or "artistic" in query_lower) and "about" not in hints:
                hints.append("about")

        # 2) Fallback to existing hardcoded heuristics if taxonomy yields nothing
        if not hints:
            if any(term in query_lower for term in ["experience", "work", "job", "role", "company", "resume", "cv"]):
                hints.append("experience")

            if any(term in query_lower for term in ["skill", "technology", "expertise", "know"]):
                hints.append("skills")

            if any(term in query_lower for term in ["about", "who", "background", "interest"]):
                hints.append("about")

            if any(
                term in query_lower for term in ["illustration", "art", "design", "creative", "inspiration", "artistic"]
            ):
                hints.append("creative")
            if "inspiration" in query_lower or "artistic" in query_lower:
                hints.append("about")

            if any(term in query_lower for term in ["project", "built", "created", "developed"]):
                hints.append("project")

        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for h in hints:
            if h not in seen:
                ordered.append(h)
                seen.add(h)
        return ordered

    def auto_route_query(self, query: str, explicit_filters: Optional[RetrievalFilters] = None) -> List[Document]:
        """
        Automatically route query to the most relevant content.
        No manual configuration needed!

        Args:
            query: User query text
            explicit_filters: Optional explicit metadata filters (overrides auto-detection)

        Returns:
            List of relevant documents
        """
        # Detect metadata filters from query or use explicit filters
        metadata_filters = explicit_filters if explicit_filters else self.detect_metadata_filters(query)

        # Also detect content type hints for legacy compatibility
        content_type_hints = self.detect_content_types(query)

        # Perform search with intelligent filtering
        if content_type_hints or metadata_filters.has_filters():
            # Use generous distance thresholds to ensure good coverage
            # Since ChromaDB returns distance scores (lower=better), higher threshold = more inclusive
            initial_threshold = AppConfig.INCLUSIVE_DISTANCE_THRESHOLD  # Include good to fair matches
            k_value = AppConfig.EXPANDED_SEARCH_K  # Get more results to ensure comprehensive coverage

            # First try filtered search with metadata filters
            results = self.semantic_searcher.semantic_search(
                query,
                k=k_value,
                filter_content_types=content_type_hints,
                score_threshold=initial_threshold,
                metadata_filters=metadata_filters if metadata_filters.has_filters() else None,
            )

            # If not enough results, broaden the search with even higher threshold
            if len(results) < (AppConfig.EXPANDED_SEARCH_K // 2):
                additional_results = self.semantic_searcher.semantic_search(
                    query,
                    k=AppConfig.EXPANDED_SEARCH_K - len(results),
                    score_threshold=AppConfig.BROAD_DISTANCE_THRESHOLD,
                )
                results.extend(additional_results)
        else:
            # No specific type detected, do general search with generous distance threshold
            results = self.semantic_searcher.semantic_search(
                query, k=AppConfig.EXPANDED_SEARCH_K, score_threshold=AppConfig.INCLUSIVE_DISTANCE_THRESHOLD
            )

        return results

    def get_search_strategy(self, query: str) -> dict:
        """
        Determine the optimal search strategy for a query.

        Args:
            query: User query text

        Returns:
            Dictionary with search strategy parameters
        """
        content_types = self.detect_content_types(query)
        query_lower = query.lower()

        strategy = {
            "content_types": content_types,
            "k": AppConfig.DEFAULT_SEARCH_K,
            "score_threshold": AppConfig.DEFAULT_DISTANCE_THRESHOLD,
            "use_expansion": False,
            "strategy_name": "default",
        }

        # Specific strategies based on query patterns
        if any(term in query_lower for term in ["resume", "cv"]):
            strategy.update(
                {
                    "k": AppConfig.EXPANDED_SEARCH_K,
                    "score_threshold": AppConfig.INCLUSIVE_DISTANCE_THRESHOLD,
                    "use_expansion": True,
                    "strategy_name": "resume_focused",
                }
            )
        elif any(term in query_lower for term in ["illustration", "art", "creative"]):
            strategy.update(
                {
                    "k": AppConfig.DEFAULT_ILLUSTRATION_COUNT,
                    "score_threshold": 0.0,  # Get all creative content
                    "strategy_name": "creative_focused",
                }
            )
        elif len(content_types) > 1:
            # Multi-type queries need broader search
            strategy.update(
                {
                    "k": AppConfig.EXPANDED_SEARCH_K,
                    "score_threshold": AppConfig.INCLUSIVE_DISTANCE_THRESHOLD,
                    "use_expansion": True,
                    "strategy_name": "multi_type",
                }
            )
        elif not content_types:
            # General queries get moderate expansion
            strategy.update(
                {
                    "k": AppConfig.EXPANDED_SEARCH_K,
                    "score_threshold": AppConfig.INCLUSIVE_DISTANCE_THRESHOLD,
                    "strategy_name": "general",
                }
            )

        logger.debug(f"Query routing strategy for '{query}': {strategy['strategy_name']}")
        return strategy

    def route_with_strategy(self, query: str, custom_strategy: Optional[dict] = None) -> List[Document]:
        """
        Route query using a specific strategy.

        Args:
            query: User query text
            custom_strategy: Optional custom strategy parameters

        Returns:
            List of relevant documents
        """
        strategy = custom_strategy or self.get_search_strategy(query)

        results = self.semantic_searcher.semantic_search(
            query,
            k=strategy["k"],
            filter_content_types=strategy["content_types"] if strategy["content_types"] else None,
            score_threshold=strategy["score_threshold"],
        )

        # Apply expansion if strategy requires it and we don't have enough results
        if strategy.get("use_expansion", False) and len(results) < (strategy["k"] // 2):
            additional_results = self.semantic_searcher.semantic_search(
                query, k=strategy["k"] - len(results), score_threshold=AppConfig.BROAD_DISTANCE_THRESHOLD
            )
            results.extend(additional_results)

        logger.info(f"Routed query '{query}' using {strategy['strategy_name']} strategy: {len(results)} results")
        return results
