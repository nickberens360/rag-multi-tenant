"""
Unit tests for query routing settings integration.
Tests that query routing settings properly control routing behavior.
"""

from unittest.mock import patch

import pytest

from backend.core.query_router import QueryRouter, QueryType
from backend.core.settings_schemas import QueryRoutingSettings


class TestQueryRoutingSettingsIntegration:
    """Test query routing settings integration across backend services."""

    def test_query_routing_settings_schema_validation(self):
        """Test that query routing settings schema validates correctly."""
        # Test valid settings
        settings = QueryRoutingSettings(
            enable_smart_routing=True,
            confidence_threshold=0.8,
            fallback_strategy="semantic_similarity",
            enable_caching=True,
            cache_ttl_seconds=600,
            enable_parallel_processing=False,
            max_retries=5,
            similarity_threshold=0.4,
            max_search_results=10,
            enable_fuzzy_matching=True,
            fuzzy_threshold=0.6,
        )

        assert settings.enable_smart_routing is True
        assert settings.confidence_threshold == 0.8
        assert settings.fallback_strategy == "semantic_similarity"
        assert settings.enable_caching is True
        assert settings.cache_ttl_seconds == 600
        assert settings.enable_parallel_processing is False
        assert settings.max_retries == 5
        assert settings.similarity_threshold == 0.4
        assert settings.max_search_results == 10
        assert settings.enable_fuzzy_matching is True
        assert settings.fuzzy_threshold == 0.6

    def test_query_routing_settings_validation_from_dict(self):
        """Test query routing settings validation from dictionary."""
        # Test with valid data including string conversions
        data = {
            "enable_smart_routing": "false",
            "confidence_threshold": "0.85",
            "fallback_strategy": "keyword_matching",
            "enable_caching": "True",
            "cache_ttl_seconds": "900",
            "enable_parallel_processing": "FALSE",
            "max_retries": "2",
            "similarity_threshold": "0.5",
            "max_search_results": "20",
            "enable_fuzzy_matching": "true",
            "fuzzy_threshold": "0.8",
        }

        settings = QueryRoutingSettings.from_dict(data)

        assert settings.enable_smart_routing is False
        assert settings.confidence_threshold == 0.85
        assert settings.fallback_strategy == "keyword_matching"
        assert settings.enable_caching is True
        assert settings.cache_ttl_seconds == 900
        assert settings.enable_parallel_processing is False
        assert settings.max_retries == 2
        assert settings.similarity_threshold == 0.5
        assert settings.max_search_results == 20
        assert settings.enable_fuzzy_matching is True
        assert settings.fuzzy_threshold == 0.8

    def test_query_routing_settings_bounds_validation(self):
        """Test that query routing settings respect bounds validation."""
        # Test confidence_threshold bounds
        data = {"confidence_threshold": 1.5}  # Above maximum (1.0)
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.confidence_threshold == 1.0  # Should be clamped to maximum

        data = {"confidence_threshold": -0.5}  # Below minimum (0.0)
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.confidence_threshold == 0.0  # Should be clamped to minimum

        # Test cache_ttl_seconds bounds
        data = {"cache_ttl_seconds": 30}  # Below minimum (60)
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.cache_ttl_seconds == 60  # Should be clamped to minimum

        data = {"cache_ttl_seconds": 5000}  # Above maximum (3600)
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.cache_ttl_seconds == 3600  # Should be clamped to maximum

        # Test max_retries bounds
        data = {"max_retries": -1}  # Below minimum (0)
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.max_retries == 0  # Should be clamped to minimum

        data = {"max_retries": 15}  # Above maximum (10)
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.max_retries == 10  # Should be clamped to maximum

    def test_query_routing_settings_invalid_values_fallback(self):
        """Test that invalid values fall back to defaults."""
        # Test invalid fallback strategy
        data = {"fallback_strategy": "unknown_strategy"}
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.fallback_strategy == "comprehensive_search"  # Default

        # Test invalid numeric values
        data = {"confidence_threshold": "not_a_number"}
        settings = QueryRoutingSettings.from_dict(data)
        assert settings.confidence_threshold == 0.75  # Default

    @pytest.mark.asyncio
    async def test_query_router_confidence_analysis(self):
        """Test query router confidence scoring."""
        router = QueryRouter()

        # Test high confidence image query
        question = "show me illustrations of cats"
        routing_settings = QueryRoutingSettings(confidence_threshold=0.7)

        with patch("backend.core.query_router.get_settings_manager") as mock_manager:
            mock_manager.return_value.get_routing_settings.return_value = routing_settings

            result = await router.route_query_with_confidence(question)

            # Should have high confidence for clear image query
            assert result["confidence"] >= 0.7
            assert result["strategy"] == "smart_routing"
            assert "search_term" in result

    @pytest.mark.asyncio
    async def test_query_router_fallback_strategy_comprehensive(self):
        """Test comprehensive search fallback strategy."""
        router = QueryRouter()

        question = "tell me something"  # Vague question should trigger fallback
        routing_settings = QueryRoutingSettings(
            confidence_threshold=0.9, fallback_strategy="comprehensive_search"  # High threshold to trigger fallback
        )

        with patch("backend.core.query_router.get_settings_manager") as mock_manager:
            mock_manager.return_value.get_routing_settings.return_value = routing_settings

            result = await router.route_query_with_confidence(question)

            # Should use fallback strategy due to low confidence
            assert result["strategy"] == "comprehensive_search"
            assert result["fallback_applied"] is True
            assert result["search_all_types"] is True

    @pytest.mark.asyncio
    async def test_query_router_fallback_strategy_semantic(self):
        """Test semantic similarity fallback strategy."""
        router = QueryRouter()

        question = "hmm"  # Very vague question
        routing_settings = QueryRoutingSettings(
            confidence_threshold=0.9, fallback_strategy="semantic_similarity"  # High threshold to trigger fallback
        )

        with patch("backend.core.query_router.get_settings_manager") as mock_manager:
            mock_manager.return_value.get_routing_settings.return_value = routing_settings

            result = await router.route_query_with_confidence(question)

            assert result["strategy"] == "semantic_similarity"
            assert result["fallback_applied"] is True
            assert result["search_method"] == "semantic_only"
            assert result["similarity_threshold"] == 0.6

    @pytest.mark.asyncio
    async def test_query_router_fallback_strategy_keyword(self):
        """Test keyword matching fallback strategy."""
        router = QueryRouter()

        question = "x"  # Minimal question
        routing_settings = QueryRoutingSettings(
            confidence_threshold=0.9, fallback_strategy="keyword_matching"  # High threshold to trigger fallback
        )

        with patch("backend.core.query_router.get_settings_manager") as mock_manager:
            mock_manager.return_value.get_routing_settings.return_value = routing_settings

            result = await router.route_query_with_confidence(question)

            assert result["strategy"] == "keyword_matching"
            assert result["fallback_applied"] is True
            assert result["search_method"] == "keyword_only"
            assert result["use_fuzzy_matching"] is True

    @pytest.mark.asyncio
    async def test_query_router_fallback_strategy_default(self):
        """Test default response fallback strategy."""
        router = QueryRouter()

        question = ""  # Empty question
        routing_settings = QueryRoutingSettings(
            confidence_threshold=0.9, fallback_strategy="default_response"  # High threshold to trigger fallback
        )

        with patch("backend.core.query_router.get_settings_manager") as mock_manager:
            mock_manager.return_value.get_routing_settings.return_value = routing_settings

            result = await router.route_query_with_confidence(question)

            assert result["strategy"] == "default_response"
            assert result["fallback_applied"] is True
            assert result["use_default_context"] is True

    @pytest.mark.asyncio
    async def test_query_router_intent_analysis(self):
        """Test query intent analysis functionality."""
        router = QueryRouter()

        test_cases = [
            ("What is Nick's experience?", "question", ["experience"]),
            (
                "Show me his technical skills",
                "question",
                ["technical", "skills"],
            ),  # "Show" gets caught by "what" check first
            ("Explain his development philosophy", "explanation", ["technical"]),
            ("Tell me about his background", "explanation", ["personal"]),
            ("Find illustrations of cats", "retrieval", ["creative"]),
            ("General question", "general", []),
        ]

        for question, expected_intent, expected_topics in test_cases:
            intent_analysis = router._analyze_query_intent(question)

            assert intent_analysis["intent"] == expected_intent
            for topic in expected_topics:
                assert topic in intent_analysis["topics"]

    def test_query_router_confidence_calculation(self):
        """Test confidence score calculation logic."""
        router = QueryRouter()

        # Test high confidence for image queries with clear search terms
        high_conf = router._calculate_confidence_score(
            "show me illustrations of cats",
            QueryType.SPECIFIC_IMAGE_SEARCH,
            "cats",
            {"intent": "retrieval", "topics": ["creative"]},
        )
        assert high_conf >= 0.8

        # Test medium confidence for general queries
        medium_conf = router._calculate_confidence_score(
            "What is Nick's experience?",
            QueryType.AI_TEXT_RESPONSE,
            None,
            {"intent": "question", "topics": ["experience"]},
        )
        assert 0.4 <= medium_conf <= 0.8

        # Test low confidence for very short queries
        low_conf = router._calculate_confidence_score(
            "x", QueryType.AI_TEXT_RESPONSE, None, {"intent": "general", "topics": []}
        )
        assert low_conf <= 0.4

    @pytest.mark.asyncio
    async def test_query_router_retry_logic(self):
        """Test configurable retry logic."""
        router = QueryRouter()

        routing_settings = QueryRoutingSettings(max_retries=3)

        with patch("backend.core.query_router.get_settings_manager") as mock_manager:
            mock_manager.return_value.get_routing_settings.return_value = routing_settings

            # Mock route_query_with_confidence to fail first few times
            call_count = 0

            async def mock_route_confidence(question, chat_history=None):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:  # Fail first 2 attempts
                    raise Exception("Temporary routing failure")
                # Succeed on 3rd attempt
                return {"strategy": "success_after_retry", "confidence": 0.8, "query_type": "ai_text_response"}

            router.route_query_with_confidence = mock_route_confidence

            result = await router.route_query_with_retries("test question")

            assert result["strategy"] == "success_after_retry"
            assert call_count == 3  # Should have tried 3 times

    @pytest.mark.asyncio
    async def test_query_router_emergency_fallback(self):
        """Test emergency fallback when all retries fail."""
        router = QueryRouter()

        routing_settings = QueryRoutingSettings(max_retries=2)

        with patch("backend.core.query_router.get_settings_manager") as mock_manager:
            mock_manager.return_value.get_routing_settings.return_value = routing_settings

            # Mock route_query_with_confidence to always fail
            async def mock_route_confidence(question, chat_history=None):
                raise Exception("Persistent routing failure")

            router.route_query_with_confidence = mock_route_confidence

            result = await router.route_query_with_retries("test question")

            assert result["strategy"] == "emergency_fallback"
            assert result["error_occurred"] is True
            assert result["confidence"] == 0.2

    def test_query_router_result_acceptability(self):
        """Test result quality validation."""
        router = QueryRouter()

        routing_settings = QueryRoutingSettings(confidence_threshold=0.7)

        # Test acceptable high-confidence result
        good_result = {"confidence": 0.8, "query_type": "specific_image_search", "strategy": "smart_routing"}
        assert router._is_result_acceptable(good_result, routing_settings) is True

        # Test unacceptable low-confidence result
        bad_result = {"confidence": 0.5, "query_type": "ai_text_response", "strategy": "smart_routing"}
        assert router._is_result_acceptable(bad_result, routing_settings) is False

        # Test acceptable fallback result (confidence threshold doesn't apply)
        fallback_result = {"confidence": 0.4, "fallback_applied": True, "strategy": "comprehensive_search"}
        assert router._is_result_acceptable(fallback_result, routing_settings) is True

        # Test emergency result (always acceptable)
        emergency_result = {
            "confidence": 0.1,
            "error_occurred": True,
            "strategy": "emergency_fallback",
            "query_type": "emergency",
        }
        assert router._is_result_acceptable(emergency_result, routing_settings) is True

    def test_query_routing_settings_json_serialization(self):
        """Test that query routing settings can be serialized to/from JSON."""
        settings = QueryRoutingSettings(
            enable_smart_routing=False,
            confidence_threshold=0.6,
            fallback_strategy="keyword_matching",
            enable_caching=False,
            cache_ttl_seconds=120,
            enable_parallel_processing=True,
            max_retries=1,
            similarity_threshold=0.2,
            max_search_results=5,
            enable_fuzzy_matching=False,
            fuzzy_threshold=0.5,
        )

        # Test serialization
        json_str = settings.to_json()
        assert isinstance(json_str, str)

        # Test deserialization
        loaded_settings = QueryRoutingSettings.from_json(json_str)
        assert loaded_settings.enable_smart_routing is False
        assert loaded_settings.confidence_threshold == 0.6
        assert loaded_settings.fallback_strategy == "keyword_matching"
        assert loaded_settings.enable_caching is False
        assert loaded_settings.cache_ttl_seconds == 120
        assert loaded_settings.enable_parallel_processing is True
        assert loaded_settings.max_retries == 1
        assert loaded_settings.similarity_threshold == 0.2
        assert loaded_settings.max_search_results == 5
        assert loaded_settings.enable_fuzzy_matching is False
        assert loaded_settings.fuzzy_threshold == 0.5

    def test_query_router_performance_logging(self):
        """Test routing performance logging."""
        router = QueryRouter()

        routing_decision = {
            "strategy": "smart_routing",
            "query_type": "specific_image_search",
            "confidence": 0.85,
            "fallback_applied": False,
            "error_occurred": False,
            "settings_applied": True,
        }

        # Should not raise any exceptions
        router.log_routing_performance(
            question="test query", routing_decision=routing_decision, processing_time=0.123, attempt_count=1
        )

        # Test with error case
        error_decision = {"strategy": "emergency_fallback", "error_occurred": True}

        router.log_routing_performance(
            question="problematic query", routing_decision=error_decision, processing_time=0.5, attempt_count=3
        )
