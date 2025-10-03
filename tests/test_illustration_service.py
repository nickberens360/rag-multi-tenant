"""Tests for smart illustration service fuzzy matching."""

from typing import Dict, cast

import pytest

from backend.core.smart_illustration_service import SmartIllustrationService
from backend.core.unified_retriever import UnifiedRetriever


class _DummyRetriever:
    def semantic_search(self, query: str, k: int = 10, filter_content_types=None, score_threshold: float = 0.5):
        # Return no results to force fuzzy fallback
        return []


class TestIllustrationService:
    @pytest.mark.unit
    def test_fuzzy_fallback_handles_typos(self):
        svc = SmartIllustrationService(unified_retriever=cast(UnifiedRetriever, _DummyRetriever()))

        # Check if illustrations cache was loaded
        if not svc._illustrations_cache:
            pytest.skip("No illustrations data available for testing")

        # Intentionally misspelled 'smalltime'
        results = svc.search("smaltime", top_k=5)
        assert results, "Expected fuzzy fallback to return at least one result"
        assert any("smalltime" in r["file"].lower() for r in results), "Should include Smalltime illustration"

    @pytest.mark.unit
    def test_search_term_cleaning(self):
        svc = SmartIllustrationService(unified_retriever=cast(UnifiedRetriever, _DummyRetriever()))

        # Test cleaning various search terms
        assert svc._clean_search_term("  hello  world  ") == "hello world"
        assert svc._clean_search_term("hello!@#world") == "hello world"
        assert svc._clean_search_term("test-case") == "test-case"
        assert svc._clean_search_term("it's working") == "it's working"

    @pytest.mark.unit
    def test_fuzzy_scoring(self):
        svc = SmartIllustrationService(unified_retriever=cast(UnifiedRetriever, _DummyRetriever()))

        entry: Dict[str, str] = {
            "file": "smalltime.png",
            "title": "Smalltime Illustration",
        }

        # Test exact match gets high score (adjusted based on weighted scoring)
        score = svc._score_entry("smalltime", entry)
        assert score > 0.7, f"Expected score > 0.7, got {score}"

        # Test typo gets reasonable score
        typo_score = svc._score_entry("smaltime", entry)
        assert 0.4 < typo_score < 0.9, f"Expected score between 0.4 and 0.9, got {typo_score}"

        # Test unrelated term gets low score
        unrelated_score = svc._score_entry("banana", entry)
        assert unrelated_score < 0.3, f"Expected score < 0.3, got {unrelated_score}"
