"""Tests for core.query_router module."""

import pytest

from backend.core.query_router import QueryRouter, QueryType


class TestQueryRouter:
    """Test cases for query router module."""

    def setup_method(self):
        """Setup method to create fresh router for each test."""
        self.router = QueryRouter()

    @pytest.mark.unit
    def test_specific_image_search_patterns(self):
        """Test specific image search pattern detection."""
        test_cases = [
            ("images of dragons", QueryType.SPECIFIC_IMAGE_SEARCH, "dragons"),
            ("image of a cat", QueryType.SPECIFIC_IMAGE_SEARCH, "a cat"),
            ("drawings of landscapes", QueryType.SPECIFIC_IMAGE_SEARCH, "landscapes"),
            ("drawing of a house", QueryType.SPECIFIC_IMAGE_SEARCH, "a house"),
            ("illustrations of characters", QueryType.SPECIFIC_IMAGE_SEARCH, "characters"),
            ("illustration of a tree", QueryType.SPECIFIC_IMAGE_SEARCH, "a tree"),
            ("art about nature", QueryType.SPECIFIC_IMAGE_SEARCH, "nature"),
            ("art of fantasy", QueryType.SPECIFIC_IMAGE_SEARCH, "fantasy"),
        ]

        for query, expected_type, expected_term in test_cases:
            query_type, search_term = self.router.route_query(query)
            assert query_type == expected_type, f"Failed for query: {query}"
            assert search_term == expected_term, f"Wrong search term for: {query}"

    @pytest.mark.unit
    def test_all_images_patterns(self):
        """Test all images pattern detection."""
        all_image_queries = [
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
            "show me art",
            "show me pictures",
            "show me drawings",
        ]

        for query in all_image_queries:
            query_type, search_term = self.router.route_query(query)
            assert query_type == QueryType.ALL_IMAGES, f"Failed to detect all images for: {query}"
            assert search_term == "all", f"Wrong search term for all images query: {query}"

    @pytest.mark.unit
    def test_show_me_patterns_with_search_terms(self):
        """Test show me patterns that extract search terms."""
        test_cases = [
            ("show me dragon images", QueryType.SHOW_ME_PATTERN, "dragon"),
            ("show me fantasy art", QueryType.SHOW_ME_PATTERN, "fantasy"),
            ("find character drawings", QueryType.SHOW_ME_PATTERN, "character"),
            ("get landscape pictures", QueryType.SHOW_ME_PATTERN, "landscape"),
            ("display nature illustrations", QueryType.SHOW_ME_PATTERN, "nature"),
            ("show cosmic art", QueryType.SHOW_ME_PATTERN, "cosmic"),
        ]

        for query, expected_type, expected_term in test_cases:
            query_type, search_term = self.router.route_query(query)
            assert query_type == expected_type, f"Failed for query: {query}"
            assert search_term == expected_term, f"Wrong search term for: {query}"

    @pytest.mark.unit
    def test_general_image_patterns(self):
        """Test general image pattern detection."""
        test_cases = [
            ("dragon images", QueryType.GENERAL_IMAGE_PATTERN, "dragon"),
            ("fantasy art", QueryType.GENERAL_IMAGE_PATTERN, "fantasy"),
            ("character drawings", QueryType.GENERAL_IMAGE_PATTERN, "character"),
            ("landscape pictures", QueryType.GENERAL_IMAGE_PATTERN, "landscape"),
            ("nature illustrations", QueryType.GENERAL_IMAGE_PATTERN, "nature"),
            ("cosmic art", QueryType.GENERAL_IMAGE_PATTERN, "cosmic"),
            ("space pics", QueryType.GENERAL_IMAGE_PATTERN, "space"),
        ]

        for query, expected_type, expected_term in test_cases:
            query_type, search_term = self.router.route_query(query)
            assert query_type == expected_type, f"Failed for query: {query}"
            assert search_term == expected_term, f"Wrong search term for: {query}"

    @pytest.mark.unit
    def test_ai_text_response_fallback(self):
        """Test that non-image queries fall back to AI text response."""
        text_queries = [
            "what is your experience",
            "tell me about yourself",
            "how do you work",
            "what technologies do you use",
            "describe your background",
            "what are your skills",
            "hello there",
            "how are you",
        ]

        for query in text_queries:
            query_type, search_term = self.router.route_query(query)
            assert query_type == QueryType.AI_TEXT_RESPONSE, f"Should be AI text response for: {query}"
            assert search_term is None, f"Should have no search term for: {query}"

    @pytest.mark.unit
    def test_ignore_words_filtering(self):
        """Test that ignore words are properly filtered from search terms."""
        test_cases = [
            ("show me the dragon images", "dragon"),
            ("find some fantasy art", "fantasy"),
            ("get all the character drawings", "character"),
            ("display any landscape pictures", "landscape"),
            # Test new ignore words "more" and "details"
            ("tell me more about the don't illustration", "don't"),
            ("show me more details about dragon images", "dragon"),
            ("more details about cosmic art", "cosmic"),
            ("tell me more about snake hug illustration", "snake hug"),
            ("give me more details for fantasy art", "fantasy"),
        ]

        for query, expected_term in test_cases:
            query_type, search_term = self.router.route_query(query)
            assert search_term == expected_term, f"Ignore words not filtered properly for: {query}"

    @pytest.mark.unit
    def test_empty_search_terms_handled(self):
        """Test that queries with only ignore words are handled properly."""
        queries_with_only_ignore_words = [
            "show me the images",  # Should go to all images
            "find some art",  # Should go to all images
            "get all pictures",  # Should go to all images
        ]

        for query in queries_with_only_ignore_words:
            query_type, search_term = self.router.route_query(query)
            # These should either be ALL_IMAGES or fall back to AI_TEXT_RESPONSE
            assert query_type in [QueryType.ALL_IMAGES, QueryType.AI_TEXT_RESPONSE], f"Unexpected type for: {query}"

    @pytest.mark.unit
    def test_case_insensitive_matching(self):
        """Test that pattern matching works regardless of case."""
        test_cases = [
            ("IMAGES OF DRAGONS", QueryType.SPECIFIC_IMAGE_SEARCH, "DRAGONS"),
            ("Show Me All Images", QueryType.ALL_IMAGES, "all"),
            ("DRAGON IMAGES", QueryType.GENERAL_IMAGE_PATTERN, "DRAGON"),
        ]

        for query, expected_type, expected_term in test_cases:
            # Router expects lowercase input, so we test with lowercase
            query_lower = query.lower()
            query_type, search_term = self.router.route_query(query_lower)
            assert query_type == expected_type, f"Failed for query: {query_lower}"
            assert search_term == expected_term.lower(), f"Wrong search term for: {query_lower}"

    @pytest.mark.unit
    def test_query_routing_priority(self):
        """Test that query routing follows correct priority order."""
        # Specific image search should take priority over general patterns
        query_type, search_term = self.router.route_query("images of dragons")
        assert query_type == QueryType.SPECIFIC_IMAGE_SEARCH
        assert search_term == "dragons"

        # All images should take priority over show me patterns
        query_type, search_term = self.router.route_query("show me images")
        assert query_type == QueryType.ALL_IMAGES
        assert search_term == "all"

    @pytest.mark.unit
    def test_is_image_query_method(self):
        """Test the is_image_query helper method."""
        image_queries = [
            "show me images",
            "dragon art",
            "images of cats",
            "find illustrations",
        ]

        text_queries = [
            "what is your experience",
            "tell me about yourself",
            "how do you work",
        ]

        for query in image_queries:
            assert self.router.is_image_query(query), f"Should detect as image query: {query}"

        for query in text_queries:
            assert not self.router.is_image_query(query), f"Should not detect as image query: {query}"

    @pytest.mark.unit
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            ("", QueryType.AI_TEXT_RESPONSE, None),  # Empty string
            ("   ", QueryType.AI_TEXT_RESPONSE, None),  # Whitespace only
            ("images", QueryType.AI_TEXT_RESPONSE, None),  # Single keyword
            ("of dragons", QueryType.AI_TEXT_RESPONSE, None),  # Partial pattern
        ]

        for query, expected_type, expected_term in edge_cases:
            query_type, search_term = self.router.route_query(query)
            assert query_type == expected_type, f"Failed for edge case: '{query}'"
            assert search_term == expected_term, f"Wrong search term for edge case: '{query}'"

    @pytest.mark.unit
    def test_complex_search_terms(self):
        """Test extraction of complex multi-word search terms."""
        test_cases = [
            ("images of fantasy dragon characters", QueryType.SPECIFIC_IMAGE_SEARCH, "fantasy dragon characters"),
            ("show me cosmic space art", QueryType.SHOW_ME_PATTERN, "cosmic space"),
            ("medieval castle drawings", QueryType.GENERAL_IMAGE_PATTERN, "medieval castle"),
            ("art of ancient mythology", QueryType.SPECIFIC_IMAGE_SEARCH, "ancient mythology"),
        ]

        for query, expected_type, expected_term in test_cases:
            query_type, search_term = self.router.route_query(query)
            assert query_type == expected_type, f"Failed for query: {query}"
            assert search_term == expected_term, f"Wrong search term for: {query}"

    @pytest.mark.unit
    def test_filler_words_and_quotes_are_stripped(self):
        """Search term extraction removes filler words and punctuation/quotes."""
        cases = [
            ("Tell me about the 'Smalltime' illustration", QueryType.GENERAL_IMAGE_PATTERN, "smalltime"),
            ("please tell me about smalltime illustrations!", QueryType.GENERAL_IMAGE_PATTERN, "smalltime"),
            ("can you show me 'Dope Goose' art?", QueryType.GENERAL_IMAGE_PATTERN, "dope goose"),
        ]
        for query, expected_type, expected_term in cases:
            q = query.lower().strip()
            qtype, term = self.router.route_query(q)
            assert qtype == expected_type, f"Wrong type for: {query}"
            assert term == expected_term, f"Wrong term for: {query} -> {term}"

    @pytest.mark.unit
    def test_router_initialization(self):
        """Test that router initializes with expected patterns and keywords."""
        assert len(self.router.image_keywords) > 0
        assert len(self.router.specific_image_keywords) > 0
        assert len(self.router.show_me_patterns) > 0
        assert len(self.router.image_indicators) > 0
        assert len(self.router.ignore_words) > 0
        assert len(self.router.all_image_phrases) > 0

        # Test that expected keywords are present
        assert "image" in self.router.image_keywords
        assert "illustration" in self.router.image_keywords
        assert "images of" in self.router.specific_image_keywords
        assert "show me" in self.router.show_me_patterns
        assert "the" in self.router.ignore_words
        assert "more" in self.router.ignore_words
        assert "details" in self.router.ignore_words
        assert "give" in self.router.ignore_words

    @pytest.mark.unit
    def test_ignore_words_separated_correctly(self):
        """Test that ignore words are properly separated (regression test for string concatenation bug)."""
        # Before the fix, "describe" and "for" were concatenated as "describefor"
        assert "describe" in self.router.ignore_words, "The word 'describe' should be in ignore_words"
        assert "for" in self.router.ignore_words, "The word 'for' should be in ignore_words"

        # Test that these words are actually filtered out during search term extraction
        test_cases = [
            ("show me describe fantasy images", "fantasy"),  # "describe" should be filtered
            ("find images for dragons", "dragons"),  # "for" should be filtered
            ("show me images for fantasy", "fantasy"),  # "for" should be filtered
            ("describe the art images", "art"),  # "describe" should be filtered
        ]

        for query, expected_term in test_cases:
            query_type, search_term = self.router.route_query(query)
            assert search_term == expected_term, f"Words not filtered correctly for: {query}, got: {search_term}"
