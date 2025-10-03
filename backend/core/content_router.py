"""
Content router component for intelligent query routing and content type detection.

This module provides focused functionality for:
- Query intent analysis and content type detection
- Smart routing based on query patterns
- Adaptive search strategy selection
- Content type hint extraction
"""

import logging
import re
from typing import List, Optional

from langchain.docstore.document import Document

from .config_v2 import AppConfig
from .semantic_searcher import SemanticSearcher
from .taxonomy_loader import get_topic_taxonomy

logger = logging.getLogger(__name__)


class ContentRouter:
    """Handles intelligent query routing and content type detection."""

    def __init__(self, semantic_searcher: SemanticSearcher):
        self.semantic_searcher = semantic_searcher

    def detect_content_types(self, query: str) -> List[str]:
        """
        Detect content types based on query patterns.

        Args:
            query: User query text

        Returns:
            List of detected content type hints
        """
        query_lower = query.lower().strip()
        hints: List[str] = []

        # 1) Try taxonomy-driven detection
        taxonomy = get_topic_taxonomy()
        if taxonomy and isinstance(taxonomy.get("categories"), dict):
            cats = taxonomy["categories"]

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

    def auto_route_query(self, query: str) -> List[Document]:
        """
        Automatically route query to the most relevant content.
        No manual configuration needed!

        Args:
            query: User query text

        Returns:
            List of relevant documents
        """
        content_type_hints = self.detect_content_types(query)

        # Perform search with intelligent filtering
        if content_type_hints:
            # Use generous distance thresholds to ensure good coverage
            # Since ChromaDB returns distance scores (lower=better), higher threshold = more inclusive
            initial_threshold = AppConfig.INCLUSIVE_DISTANCE_THRESHOLD  # Include good to fair matches
            k_value = AppConfig.EXPANDED_SEARCH_K  # Get more results to ensure comprehensive coverage

            # First try filtered search
            results = self.semantic_searcher.semantic_search(
                query, k=k_value, filter_content_types=content_type_hints, score_threshold=initial_threshold
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
