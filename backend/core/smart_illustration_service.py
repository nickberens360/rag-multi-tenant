"""
Smart illustration service using unified retriever.

This service replaces the old illustration service and unified_data.json dependency
with intelligent illustration search using the unified retriever system.
"""

import json
import logging
import re
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

from .config_v2 import AppConfig
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class SmartIllustrationService:
    """Smart illustration service that uses unified retriever for image search."""

    def __init__(self, unified_retriever: UnifiedRetriever):
        self.unified_retriever = unified_retriever
        # Cache illustrations data to avoid repeated file I/O
        self._illustrations_cache = self._load_illustrations_data()
        # Cache for search results to improve performance
        self._search_cache: Dict[str, List[Dict[str, str]]] = {}
        # Cache all illustrations for faster retrieval
        self._all_illustrations_cache: Optional[List[Dict[str, str]]] = None

    def validate_data(self):
        """Validate that illustration data is available."""
        try:
            # Test search for illustrations to see if data exists
            test_results = self.search("illustration", top_k=1)
            if test_results:
                return True, "✅ Smart illustration system ready with unified retriever."
            else:
                return False, "❌ No illustration data found in unified retriever."
        except Exception as e:
            logger.warning(f"Illustration validation failed: {e}")
            return False, f"❌ Illustration validation failed: {e}"

    def get_all(self) -> List[Dict[str, str]]:
        """Return all illustrations using metadata filtering with caching."""
        # Return cached results if available
        if self._all_illustrations_cache is not None:
            logger.info(f"Returning cached all illustrations: {len(self._all_illustrations_cache)} items")
            return self._all_illustrations_cache

        try:
            logger.info("Attempting to get all illustrations using metadata filtering...")

            # Use semantic search with creative content type filter
            docs = self.unified_retriever.semantic_search(
                query="illustration art design creative",
                k=AppConfig.MAX_ILLUSTRATION_SEARCH,  # High enough to get all illustrations
                filter_content_types=["creative"],
                score_threshold=0.0,  # Get all results (no distance filtering)
            )

            logger.debug(f"Semantic search returned {len(docs)} documents")
            for i, doc in enumerate(docs[:5]):  # Debug first 5 docs
                logger.debug(f"Doc {i}: metadata = {doc.metadata}")

            illustrations: List[Dict[str, str]] = []
            seen_files = set()

            for doc in docs:
                is_illustration = doc.metadata.get("is_illustration_data")
                logger.debug(
                    f"Processing doc: is_illustration_data={is_illustration}, metadata keys={list(doc.metadata.keys())}"
                )

                if is_illustration:
                    display_path = doc.metadata.get("display_path")
                    file_key = doc.metadata.get("illustration_file")
                    logger.debug(f"Found illustration: display_path={display_path}, file_key={file_key}")

                    if display_path and file_key not in seen_files:
                        illustrations.append({"file": display_path})
                        seen_files.add(file_key)

            logger.debug(f"Found {len(illustrations)} illustrations via metadata filtering")
            # Cache the results
            self._all_illustrations_cache = illustrations
            return illustrations

        except Exception:
            logger.error("Failed to get all illustrations", exc_info=True)
            return []

    def search(self, search_term: str, top_k: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Search illustrations using smart retriever with caching and improved matching.

        Args:
            search_term: The user's search query
            top_k: Maximum number of results (defaults to AppConfig.DEFAULT_ILLUSTRATION_COUNT)

        Returns:
            List of illustration file paths for frontend display
        """
        if not search_term or not isinstance(search_term, str):
            logger.warning("Invalid search term provided to illustration search.")
            return []

        # Apply default from config
        if top_k is None:
            top_k = AppConfig.DEFAULT_ILLUSTRATION_COUNT

        # Clean and normalize the search term
        cleaned_term = self._clean_search_term(search_term)

        # Check cache first
        cache_key = f"{cleaned_term}:{top_k}"
        if cache_key in self._search_cache:
            logger.info(f"Returning cached results for '{cleaned_term}'")
            return self._search_cache[cache_key]

        logger.info(f"Smart illustration search for: '{cleaned_term}' (original: '{search_term}')")

        try:
            # Special case: if asking for "all", use get_all method
            if cleaned_term.lower() == "all":
                return self.get_all()

            # Use semantic search with creative content type filter and search term
            docs = self.unified_retriever.semantic_search(
                query=f"{cleaned_term} illustration art creative character",
                k=top_k * 3,  # Get more docs to allow better filtering
                filter_content_types=["creative"],
                score_threshold=0.0,  # Get all results (no distance filtering)
            )

            illustrations: List[Dict[str, str]] = []
            seen_files = set()

            for doc in docs:
                if len(illustrations) >= top_k:
                    break

                if doc.metadata.get("is_illustration_data"):
                    # Check if search term matches content for specific searches
                    content_lower = doc.page_content.lower()
                    search_lower = cleaned_term.lower()

                    # Improved matching: check for exact match, partial match, or "all"
                    if (
                        cleaned_term.lower() == "all"
                        or search_lower in content_lower
                        or self._is_fuzzy_match(search_lower, content_lower)
                    ):
                        display_path = doc.metadata.get("display_path")
                        file_key = doc.metadata.get("illustration_file")

                        if display_path and file_key not in seen_files:
                            illustrations.append({"file": display_path})
                            seen_files.add(file_key)
                            logger.debug(f"Found illustration via search: {file_key} -> {display_path}")

            logger.debug(f"Smart illustration search returned {len(illustrations)} results for '{cleaned_term}'")

            # Enhanced fuzzy fallback: always try fuzzy matching for better results
            if len(illustrations) < top_k:
                try:
                    fuzzy_needed = top_k - len(illustrations)
                    extra = self._fuzzy_fallback(cleaned_term, fuzzy_needed, seen_files)
                    illustrations.extend(extra)
                    logger.debug(
                        f"Fuzzy fallback added {len(extra)} results; total now {len(illustrations)} for "
                        f"'{cleaned_term}'"
                    )
                except Exception:
                    logger.warning("Fuzzy fallback failed", exc_info=True)

            # Cache the results
            result = illustrations[:top_k]
            self._search_cache[cache_key] = result
            return result

        except Exception:
            logger.error("Smart illustration search failed", exc_info=True)
            return []

    # --- Internal helpers ---
    def _clean_search_term(self, term: str) -> str:
        """Clean and normalize search terms for better matching.

        Improvements:
        - Prefer quoted phrases (e.g., 'Hide Out') as the primary key
        - Remove common intent/filler words (e.g., describe, show, illustration)
        - Strip stray quotes around tokens
        """
        if not term:
            return ""

        # Normalize whitespace
        s = " ".join(term.strip().split())

        # Prefer the longest quoted phrase if present
        quoted = re.findall(r"[\"']([^\"']+)[\"']", s)
        if quoted:
            primary = max((q.strip() for q in quoted), key=len)
            return " ".join(primary.split())

        # Remove punctuation except hyphens and apostrophes
        s = re.sub(r"[^\w\s\-\']", " ", s)
        s = " ".join(s.split())

        stopwords = {
            "describe",
            "show",
            "see",
            "find",
            "display",
            "list",
            "tell",
            "about",
            "please",
            "me",
            "the",
            "a",
            "an",
            "of",
            "for",
            "this",
            "that",
            "illustration",
            "illustrations",
            "image",
            "images",
            "art",
            "picture",
            "titled",
            "called",
        }

        tokens: List[str] = []
        for tok in s.split():
            tok_norm = tok.strip("'\"")
            if tok_norm and tok_norm.lower() not in stopwords:
                tokens.append(tok_norm)

        cleaned = " ".join(tokens) if tokens else s

        # Special case: if we're left with just possessive forms like "nick's", "nicks", etc.
        # treat it as a request for all illustrations
        if cleaned.lower() in ["nick's", "nicks", "nick", "my", "his", "her"]:
            cleaned = "all"

        return " ".join(cleaned.split())

    def _is_fuzzy_match(self, search: str, content: str, threshold: Optional[float] = None) -> bool:
        """Check if search term is a fuzzy match for content."""
        if threshold is None:
            threshold = AppConfig.DEFAULT_FUZZY_THRESHOLD

        # Split into words for word-level matching
        search_words = search.split()
        content_words = content.split()

        # Check if all search words have a fuzzy match in content
        for search_word in search_words:
            best_score = 0.0
            for content_word in content_words:
                score = SequenceMatcher(None, search_word, content_word).ratio()
                best_score = max(best_score, score)

            if best_score < threshold:
                return False

        return True

    def _load_illustrations_data(self) -> List[Dict[str, str]]:
        """Load illustrations from configured JSON file with caching."""
        path = AppConfig.ILLUSTRATIONS_PATH
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    logger.info(f"Loaded {len(data)} illustrations from {path}")
                    return data
        except Exception:
            logger.warning(f"Unable to load illustrations from {path}", exc_info=True)
        return []

    def _score_entry(self, search: str, entry: Dict[str, str]) -> float:
        """Enhanced fuzzy scoring with weighted components."""
        s = search.lower().strip()
        title = (entry.get("title") or "").lower()
        # Normalize tags: ensure a list of strings before joining
        raw_tags = entry.get("tags")
        tags_list: List[str]
        if isinstance(raw_tags, list):
            tags_list = [str(tag).strip() for tag in raw_tags if tag is not None]
        elif isinstance(raw_tags, str):
            tags_list = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
        else:
            tags_list = []
        tags = " ".join(tags_list).lower()
        file_name = (entry.get("file") or "").lower()

        scores: List[Tuple[float, float]] = []  # (score, weight)

        # Title matching (highest weight)
        if title:
            title_score = SequenceMatcher(None, s, title).ratio()
            scores.append((title_score, 2.0))

            # Bonus for exact title match
            if s == title:
                scores.append((1.0, 3.0))

        # Tag matching (medium weight)
        if tags:
            tag_score = SequenceMatcher(None, s, tags).ratio()
            scores.append((tag_score, 1.5))

            # Check individual tags using normalized list
            for tag in tags_list:
                if s == tag.lower():
                    scores.append((1.0, 2.0))
                elif s in tag.lower() or tag.lower() in s:
                    scores.append((0.8, 1.5))

        # Filename matching (lower weight)
        if file_name:
            # Remove extension for better matching
            clean_file = re.sub(r"\.[^.]+$", "", file_name)
            file_score = SequenceMatcher(None, s, clean_file).ratio()
            scores.append((file_score, 1.0))

        # Containment bonus
        if s and (s in title or s in tags or s in file_name):
            scores.append((0.9, 1.5))

        # Calculate weighted average
        if scores:
            total_score = sum(score * weight for score, weight in scores)
            total_weight = sum(weight for _, weight in scores)
            return total_score / total_weight

        return 0.0

    def _fuzzy_fallback(self, search_term: str, limit: int, seen_files: set) -> List[Dict[str, str]]:
        """Enhanced fuzzy fallback with adaptive thresholds."""
        entries = self._illustrations_cache
        if not entries:
            return []

        scored: List[Tuple[float, Dict[str, str]]] = []
        for e in entries:
            score = self._score_entry(search_term, e)
            # Adaptive threshold: more forgiving for shorter terms and typos
            # Use different thresholds based on term length
            if len(search_term) <= AppConfig.SHORT_TERM_LENGTH:
                threshold = AppConfig.SHORT_TERM_FUZZY_THRESHOLD
            elif len(search_term) <= AppConfig.MEDIUM_TERM_LENGTH:
                threshold = AppConfig.MEDIUM_TERM_FUZZY_THRESHOLD
            else:
                threshold = AppConfig.LONG_TERM_FUZZY_THRESHOLD

            if score >= threshold:
                scored.append((score, e))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results: List[Dict[str, str]] = []
        for score, e in scored:
            file_key = e.get("file")
            if not file_key or file_key in seen_files:
                continue
            results.append({"file": f"/illustrations/{file_key}"})
            seen_files.add(file_key)
            logger.debug(f"Fuzzy match: '{search_term}' -> '{e.get('title', file_key)}' (score: {score:.2f})")
            if len(results) >= limit:
                break

        return results

    def clear_cache(self):
        """Clear all cached data for fresh results."""
        self._search_cache.clear()
        self._all_illustrations_cache = None
        logger.info("Illustration service cache cleared")
