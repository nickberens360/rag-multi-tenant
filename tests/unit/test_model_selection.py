"""
Unit tests for model selection functionality.

Tests the select_optimal_model_for_query function to ensure proper model selection
based on query complexity and user preferences.
"""

import pytest

from backend.core.llm_chain import select_optimal_model_for_query


class TestSelectOptimalModelForQuery:
    """Test cases for select_optimal_model_for_query function."""

    def test_user_preference_overrides_smart_selection(self):
        """Test that user preferences override smart model selection."""
        query = "explain complex architecture patterns"  # Would normally use claude
        preferred_model = "claude_haiku"

        result = select_optimal_model_for_query(query, preferred_model)
        assert result == "claude_haiku"

    def test_simple_query_selects_haiku(self):
        """Test that simple queries select Claude Haiku for speed."""
        simple_queries = [
            "what programming languages do you know",
            "list your skills",
            "show me your experience with Python",
            "tell me about your background in web development",
            "what technologies are you familiar with",
        ]

        for query in simple_queries:
            result = select_optimal_model_for_query(query)
            assert result == "claude_haiku", f"Query '{query}' should use claude_haiku"

    def test_complex_query_selects_sonnet(self):
        """Test that complex queries select Claude Sonnet for quality."""
        complex_queries = [
            "how does microservices architecture compare to monoliths",
            "explain your approach to system design",
            "why do you prefer certain design patterns",
            "analyze the best practices for API development",
            "compare different frontend frameworks and their trade-offs",
            "what is your philosophy on software architecture",
        ]

        for query in complex_queries:
            result = select_optimal_model_for_query(query)
            assert result == "claude", f"Query '{query}' should use claude"

    def test_short_simple_query_selects_haiku(self):
        """Test that short, simple queries select Haiku."""
        short_queries = [
            "list skills",
            "show experience",
            "what languages",
            "background",
        ]

        for query in short_queries:
            result = select_optimal_model_for_query(query)
            assert result == "claude_haiku", f"Query '{query}' should use claude_haiku"

    def test_moderate_query_defaults_to_haiku(self):
        """Test that moderate queries default to Haiku for speed."""
        moderate_queries = [
            "Tell me about your work at previous companies",
            "What projects have you worked on recently",
            "Describe your development workflow",
        ]

        for query in moderate_queries:
            result = select_optimal_model_for_query(query)
            assert result == "claude_haiku", f"Query '{query}' should default to claude_haiku"

    def test_mixed_complexity_indicators(self):
        """Test queries with both simple and complex indicators."""
        # Should favor complex indicators
        mixed_query = "list the technologies you use and explain why you chose them"
        result = select_optimal_model_for_query(mixed_query)
        assert result == "claude", "Mixed queries with 'explain' should use claude"

    def test_invalid_preferred_model_uses_smart_selection(self):
        """Test that invalid preferred models fall back to smart selection."""
        query = "what programming languages do you know"
        invalid_model = "nonexistent_model"

        result = select_optimal_model_for_query(query, invalid_model)
        assert result == "claude_haiku", "Should fall back to smart selection for invalid model"

    def test_empty_query_defaults_to_haiku(self):
        """Test that empty or minimal queries default to Haiku."""
        empty_queries = ["", " ", "hi", "hello"]

        for query in empty_queries:
            result = select_optimal_model_for_query(query)
            assert result == "claude_haiku", f"Empty/minimal query '{query}' should use claude_haiku"

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case insensitive."""
        queries = [
            "WHAT PROGRAMMING LANGUAGES",
            "Show Me Your Skills",
            "EXPLAIN YOUR APPROACH",
            "Why Do You Prefer",
        ]

        # First two should be simple (haiku), last two complex (claude)
        assert select_optimal_model_for_query(queries[0]) == "claude_haiku"
        assert select_optimal_model_for_query(queries[1]) == "claude_haiku"
        assert select_optimal_model_for_query(queries[2]) == "claude"
        assert select_optimal_model_for_query(queries[3]) == "claude"

    def test_query_length_threshold(self):
        """Test that query length affects model selection."""
        # Short query with no specific indicators should use haiku
        short_query = "recent work"  # 2 words, <= 10 threshold
        assert select_optimal_model_for_query(short_query) == "claude_haiku"

        # Longer query without specific indicators should use haiku (default)
        long_query = "tell me about your recent work at companies and projects you have worked on"  # >10 words
        assert select_optimal_model_for_query(long_query) == "claude_haiku"

    @pytest.mark.parametrize("model_name", ["claude", "claude_haiku", "gemini"])
    def test_valid_model_preferences(self, model_name):
        """Test that all valid model names are accepted as preferences."""
        query = "any query"
        result = select_optimal_model_for_query(query, model_name)
        assert result == model_name
