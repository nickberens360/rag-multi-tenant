"""Tests for core.llm_chain module."""

import time
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.retrievers import BaseRetriever

from backend.core.llm_chain import (
    RateLimitTracker,
    cache_response,
    cache_retrieval,
    get_cache_key,
    get_cached_response,
    get_cached_retrieval,
    get_llm_instances,
    get_rate_limit_status,
    is_rate_limit_error,
    route_query_to_retrievers,
    stream_with_fallback,
)


class TestLLMChain:
    """Test cases for LLM chain module."""

    def setup_method(self):
        """Setup method to clear caches before each test."""
        # Clear caches before each test
        import backend.core.llm_chain as llm_chain

        llm_chain._response_cache.clear()
        llm_chain._retrieval_cache.clear()

        # Reset rate limit tracker to clean state
        llm_chain.rate_limit_tracker._rate_limit_status.clear()
        llm_chain.rate_limit_tracker._rate_limit_reset_time.clear()

    @pytest.mark.unit
    def test_get_cache_key_valid_input(self):
        """Test cache key generation with valid input."""
        user_input = "What is Nick's experience?"
        cache_key = get_cache_key(user_input)

        # Should return a 64-character hex string (full SHA256)
        assert cache_key is not None
        assert len(cache_key) == 64
        assert all(c in "0123456789abcdef" for c in cache_key)

        # Same input should produce same key
        cache_key2 = get_cache_key(user_input)
        assert cache_key == cache_key2

    @pytest.mark.unit
    def test_get_cache_key_normalization(self):
        """Test that cache key normalizes input correctly."""
        # Different punctuation and case should produce same key
        inputs = [
            "What is Nick's experience?",
            "what is nicks experience",
            "WHAT IS NICK'S EXPERIENCE!!!",
            "What... is Nick's experience???",
        ]

        cache_keys = [get_cache_key(inp) for inp in inputs]
        # All should be the same after normalization
        assert len(set(cache_keys)) == 1

    @patch("backend.core.llm_chain.ENABLE_CACHING", False)
    @pytest.mark.unit
    def test_get_cache_key_caching_disabled(self):
        """Test cache key returns None when caching is disabled."""
        cache_key = get_cache_key("test input")
        assert cache_key is None

    @pytest.mark.unit
    def test_get_cache_key_invalid_input(self):
        """Test cache key with invalid input types."""
        assert get_cache_key(None) is None
        assert get_cache_key(123) is None  # type: ignore[arg-type]
        assert get_cache_key([]) is None  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_cache_response_and_get_cached_response(self):
        """Test response caching and retrieval."""
        cache_key = "test_key_123"
        response_chunks = ["Hello ", "world", "!"]

        # Cache the response
        cache_response(cache_key, response_chunks)

        # Retrieve the cached response
        cached = get_cached_response(cache_key)
        assert cached == "Hello world!"

    @pytest.mark.unit
    def test_get_cached_response_expired(self):
        """Test that expired cache entries are removed."""
        cache_key = "expired_key"
        response_chunks = ["test response"]

        # Cache the response
        cache_response(cache_key, response_chunks)

        # Manually set timestamp to past expiry
        import backend.core.llm_chain as llm_chain

        llm_chain._response_cache[cache_key]["timestamp"] = time.time() - 7200  # 2 hours ago

        # Should return None and remove expired entry
        cached = get_cached_response(cache_key)
        assert cached is None
        assert cache_key not in llm_chain._response_cache

    @pytest.mark.unit
    def test_get_cached_response_not_found(self):
        """Test cache miss returns None."""
        cached = get_cached_response("nonexistent_key")
        assert cached is None

    @patch("backend.core.llm_chain.ENABLE_CACHING", False)
    @pytest.mark.unit
    def test_cache_response_caching_disabled(self):
        """Test that caching is skipped when disabled."""
        cache_key = "test_key"
        response_chunks = ["test"]

        cache_response(cache_key, response_chunks)
        cached = get_cached_response(cache_key)

        assert cached is None

    @patch("backend.core.llm_chain.ENABLE_CACHING", False)
    @pytest.mark.unit
    def test_cache_retrieval_caching_disabled(self):
        """Test that retrieval caching is skipped when disabled."""
        cache_key = "test_key"
        documents = [Document(page_content="Test", metadata={"source": "test"})]

        cache_retrieval(cache_key, documents)
        cached = get_cached_retrieval(cache_key)

        assert cached is None

    @pytest.mark.unit
    def test_cache_response_eviction(self):
        """Test cache eviction when max size is reached."""
        import backend.core.llm_chain as llm_chain

        # Mock get_max_cache_size to be small
        with patch("backend.core.llm_chain.get_max_cache_size", return_value=2):
            # Add entries up to limit
            cache_response("key1", ["response1"])
            cache_response("key2", ["response2"])

            # Add one more - should evict oldest
            time.sleep(0.01)  # Ensure different timestamps
            cache_response("key3", ["response3"])

            # key1 should be evicted, key2 and key3 should remain
            assert len(llm_chain._response_cache) == 2
            assert "key1" not in llm_chain._response_cache
            assert "key2" in llm_chain._response_cache
            assert "key3" in llm_chain._response_cache

    @pytest.mark.unit
    def test_cache_retrieval_and_get_cached_retrieval(self):
        """Test document retrieval caching and retrieval."""
        cache_key = "retrieval_key"
        documents = [
            Document(page_content="Test doc 1", metadata={"source": "test"}),
            Document(page_content="Test doc 2", metadata={"source": "test"}),
        ]

        # Cache the documents
        cache_retrieval(cache_key, documents)

        # Retrieve cached documents
        cached_docs = get_cached_retrieval(cache_key)
        assert cached_docs is not None
        assert len(cached_docs) == 2
        assert cached_docs[0].page_content == "Test doc 1"
        assert cached_docs[1].page_content == "Test doc 2"

    @pytest.mark.unit
    def test_route_query_to_retrievers_with_unified_retriever(self):
        """Test query routing with unified retriever system."""
        mock_unified_retriever = MagicMock(spec=BaseRetriever)
        mock_retrievers: Dict[str, BaseRetriever] = {
            "unified": mock_unified_retriever,
        }

        queries = [
            "What is Nick's work experience?",
            "Tell me about his job history",
            "What skills does he have?",
            "What companies has he worked for?",
        ]

        for query in queries:
            retrievers_list = route_query_to_retrievers(query, mock_retrievers)
            assert mock_unified_retriever in retrievers_list
            assert len(retrievers_list) == 1

    @pytest.mark.unit
    def test_route_query_to_retrievers_missing_unified_retriever(self):
        """Test query routing when unified retriever is missing."""
        # No unified retriever provided
        mock_retrievers: Dict[str, BaseRetriever] = {"resume": MagicMock(spec=BaseRetriever)}

        query = "Tell me about Nick's background"
        retrievers_list = route_query_to_retrievers(query, mock_retrievers)

        # Should return empty list when unified retriever is not available
        assert len(retrievers_list) == 0

    @patch("backend.core.llm_chain.LLM_PROVIDERS")
    @pytest.mark.unit
    def test_get_llm_instances_success(self, mock_providers):
        """Test successful LLM instance creation."""
        mock_claude_class = MagicMock()
        mock_gemini_class = MagicMock()
        mock_claude_instance = MagicMock()
        mock_gemini_instance = MagicMock()

        mock_claude_class.return_value = mock_claude_instance
        mock_gemini_class.return_value = mock_gemini_instance

        # Mock the LLM_PROVIDERS configuration
        mock_providers.__iter__ = MagicMock(
            return_value=iter(
                [
                    {
                        "name": "claude",
                        "class": mock_claude_class,
                        "model": "claude-3-sonnet",
                        "init_kwargs": {"model": "claude-3-sonnet", "temperature": 0.7, "timeout": 30},
                    },
                    {
                        "name": "gemini",
                        "class": mock_gemini_class,
                        "model": "gemini-pro",
                        "init_kwargs": {"model": "gemini-pro", "temperature": 0.7, "timeout": 30},
                    },
                ]
            )
        )

        llms = get_llm_instances()

        # Check that the returned instances are the mocked ones
        assert llms["claude"] is mock_claude_instance
        assert llms["gemini"] is mock_gemini_instance
        mock_claude_class.assert_called_once()
        mock_gemini_class.assert_called_once()

    @patch("backend.core.llm_chain.LLM_PROVIDERS")
    @pytest.mark.unit
    def test_get_llm_instances_claude_fails(self, mock_providers):
        """Test LLM instance creation when Claude fails."""
        mock_claude_class = MagicMock()
        mock_gemini_class = MagicMock()
        mock_gemini_instance = MagicMock()

        mock_claude_class.side_effect = Exception("Claude API error")
        mock_gemini_class.return_value = mock_gemini_instance

        # Mock the LLM_PROVIDERS configuration
        mock_providers.__iter__ = MagicMock(
            return_value=iter(
                [
                    {
                        "name": "claude",
                        "class": mock_claude_class,
                        "model": "claude-3-sonnet",
                        "init_kwargs": {"model": "claude-3-sonnet", "temperature": 0.7, "timeout": 30},
                    },
                    {
                        "name": "gemini",
                        "class": mock_gemini_class,
                        "model": "gemini-pro",
                        "init_kwargs": {"model": "gemini-pro", "temperature": 0.7, "timeout": 30},
                    },
                ]
            )
        )

        llms = get_llm_instances()

        assert llms["claude"] is None
        assert llms["gemini"] is mock_gemini_instance

    @patch("backend.core.llm_chain.LLM_PROVIDERS")
    @pytest.mark.unit
    def test_get_llm_instances_all_fail(self, mock_providers):
        """Test LLM instance creation when all models fail."""
        mock_claude_class = MagicMock()
        mock_gemini_class = MagicMock()

        mock_claude_class.side_effect = Exception("Claude API error")
        mock_gemini_class.side_effect = Exception("Gemini API error")

        # Mock the LLM_PROVIDERS configuration
        mock_providers.__iter__ = MagicMock(
            return_value=iter(
                [
                    {
                        "name": "claude",
                        "class": mock_claude_class,
                        "model": "claude-3-sonnet",
                        "init_kwargs": {"model": "claude-3-sonnet", "temperature": 0.7, "timeout": 30},
                    },
                    {
                        "name": "gemini",
                        "class": mock_gemini_class,
                        "model": "gemini-pro",
                        "init_kwargs": {"model": "gemini-pro", "temperature": 30},
                    },
                ]
            )
        )

        # The function should raise RuntimeError when no models can be initialized
        with pytest.raises(RuntimeError, match="No LLM models could be initialized"):
            get_llm_instances()

    @pytest.mark.unit
    def test_get_cached_retrieval_expired(self):
        """Test that expired retrieval cache entries are removed."""
        cache_key = "expired_retrieval_key"
        documents = [Document(page_content="Test", metadata={"source": "test"})]

        # Cache the documents
        cache_retrieval(cache_key, documents)

        # Manually set timestamp to past expiry
        import backend.core.llm_chain as llm_chain

        llm_chain._retrieval_cache[cache_key]["timestamp"] = time.time() - 7200  # 2 hours ago

        # Should return None and remove expired entry
        cached = get_cached_retrieval(cache_key)
        assert cached is None
        assert cache_key not in llm_chain._retrieval_cache

    @pytest.mark.unit
    def test_cache_retrieval_eviction(self):
        """Test retrieval cache eviction when max size is reached."""
        import backend.core.llm_chain as llm_chain

        # Mock get_max_cache_size to be small
        with patch("backend.core.llm_chain.get_max_cache_size", return_value=2):
            doc1 = [Document(page_content="Doc 1", metadata={"source": "test"})]
            doc2 = [Document(page_content="Doc 2", metadata={"source": "test"})]
            doc3 = [Document(page_content="Doc 3", metadata={"source": "test"})]

            # Add entries up to limit
            cache_retrieval("key1", doc1)
            cache_retrieval("key2", doc2)

            # Add one more - should evict oldest
            time.sleep(0.01)  # Ensure different timestamps
            cache_retrieval("key3", doc3)

            # key1 should be evicted, key2 and key3 should remain
            assert len(llm_chain._retrieval_cache) == 2
            assert "key1" not in llm_chain._retrieval_cache
            assert "key2" in llm_chain._retrieval_cache
            assert "key3" in llm_chain._retrieval_cache

    @patch("backend.core.llm_chain.CacheManager.get_cached_response")
    @patch("backend.core.llm_chain.CacheManager.get_cache_key")
    @patch("backend.core.llm_chain.get_llm_instances")
    @pytest.mark.asyncio
    async def test_stream_with_fallback_cached_response(self, mock_get_llms, mock_get_cache_key, mock_cached_response):
        """Test stream_with_fallback returns cached response when available."""
        mock_get_cache_key.return_value = "test_cache_key"
        mock_cached_response.return_value = "Cached response"

        retrievers: Dict[str, BaseRetriever] = {"resume": MagicMock(spec=BaseRetriever)}
        chat_history: List[BaseMessage] = []
        user_input = "Test question"

        stream, model_used, metadata = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        assert result == ["Cached response"]
        assert model_used == "cached"
        # Should not call other functions when cache hit
        mock_get_llms.assert_not_called()

    @patch("backend.core.llm_chain.CacheManager.get_cached_response")
    @patch("backend.core.llm_chain.CacheManager.get_cache_key")
    @patch("backend.core.llm_chain.get_llm_instances")
    @pytest.mark.asyncio
    async def test_stream_with_fallback_llm_init_error(self, mock_get_llms, mock_get_cache_key, mock_cached_response):
        """Test stream_with_fallback handles LLM initialization errors."""
        mock_get_cache_key.return_value = "test_cache_key"
        mock_cached_response.return_value = None  # No cached response
        mock_get_llms.side_effect = RuntimeError("LLM init failed")

        retrievers: Dict[str, BaseRetriever] = {"resume": MagicMock(spec=BaseRetriever)}
        chat_history: List[BaseMessage] = []
        user_input = "Test question"

        stream, model_used, metadata = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        assert len(result) == 1
        assert "AI service is temporarily unavailable" in result[0]
        assert model_used == "error"

    @patch("backend.core.llm_chain.route_query_to_retrievers")
    @patch("backend.core.llm_chain.CacheManager.get_cached_retrieval")
    @patch("backend.core.llm_chain.CacheManager.get_cached_response")
    @patch("backend.core.llm_chain.CacheManager.get_cache_key")
    @patch("backend.core.llm_chain.get_llm_instances")
    @patch("backend.core.llm_chain.create_qa_chain")
    @pytest.mark.asyncio
    async def test_stream_with_fallback_normal_flow(
        self,
        mock_create_qa_chain,
        mock_get_llms,
        mock_get_cache_key,
        mock_cached_response,
        mock_cached_retrieval,
        mock_route,
    ):
        """Test stream_with_fallback normal execution flow."""
        # Setup mocks
        mock_get_cache_key.return_value = "test_cache_key"
        mock_cached_response.return_value = None  # No cached response
        mock_cached_retrieval.return_value = None  # No cached retrieval

        # Mock LLM instances
        mock_claude = MagicMock()
        mock_get_llms.return_value = {"claude": mock_claude, "gemini": None}

        # Mock QA chain
        mock_qa_chain = AsyncMock()

        async def mock_astream(*args, **kwargs):
            for chunk in ["Hello", " world"]:
                yield chunk

        mock_qa_chain.astream = mock_astream
        mock_create_qa_chain.return_value = mock_qa_chain

        # Mock retrievers and routing
        mock_retriever = AsyncMock(spec=BaseRetriever)
        mock_retriever.ainvoke.return_value = [Document(page_content="Test content", metadata={"source": "test"})]
        mock_route.return_value = [mock_retriever]

        retrievers: Dict[str, BaseRetriever] = {"resume": mock_retriever}
        chat_history: List[BaseMessage] = []
        user_input = "Test question"

        stream, model_used, metadata = await stream_with_fallback(retrievers, chat_history, user_input)

        result = []
        async for chunk in stream:
            result.append(chunk)

        assert result == ["Hello", " world"]
        assert model_used == "claude"
        assert "rate_limit_status" in metadata


class TestRateLimitTracker:
    """Test cases for RateLimitTracker class."""

    def setup_method(self):
        """Setup method to create fresh tracker for each test."""
        self.tracker = RateLimitTracker()

    @pytest.mark.unit
    def test_initial_state(self):
        """Test tracker starts with no rate limits."""
        assert not self.tracker.is_rate_limited("claude")
        assert not self.tracker.is_rate_limited("gemini")
        assert self.tracker.get_status() == {}

    @pytest.mark.unit
    def test_set_rate_limited(self):
        """Test setting a provider as rate limited."""
        self.tracker.set_rate_limited("claude", reset_minutes=60)

        assert self.tracker.is_rate_limited("claude")
        assert not self.tracker.is_rate_limited("gemini")

        status = self.tracker.get_status()
        assert status["claude"] is True
        assert "gemini" not in status

    @pytest.mark.unit
    def test_clear_rate_limit(self):
        """Test clearing rate limit for a provider."""
        self.tracker.set_rate_limited("claude", reset_minutes=60)
        assert self.tracker.is_rate_limited("claude")

        self.tracker.clear_rate_limit("claude")
        assert not self.tracker.is_rate_limited("claude")

        status = self.tracker.get_status()
        assert status.get("claude", False) is False

    @pytest.mark.unit
    def test_rate_limit_expiration(self):
        """Test that rate limits expire after the specified time."""
        # Set rate limit with very short duration (1 minute minimum for int)
        self.tracker.set_rate_limited("claude", reset_minutes=1)

        assert self.tracker.is_rate_limited("claude")

        # Manually expire the rate limit by setting past reset time
        import datetime

        past_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        self.tracker._rate_limit_reset_time["claude"] = past_time

        # Should automatically clear when checked
        assert not self.tracker.is_rate_limited("claude")

    @pytest.mark.unit
    def test_multiple_providers_rate_limited(self):
        """Test handling multiple providers being rate limited."""
        self.tracker.set_rate_limited("claude", reset_minutes=60)
        self.tracker.set_rate_limited("gemini", reset_minutes=30)

        assert self.tracker.is_rate_limited("claude")
        assert self.tracker.is_rate_limited("gemini")

        status = self.tracker.get_status()
        assert status["claude"] is True
        assert status["gemini"] is True

    @pytest.mark.unit
    def test_get_status_cleans_expired_limits(self):
        """Test that get_status() cleans up expired rate limits."""
        # Set rate limit
        self.tracker.set_rate_limited("claude", reset_minutes=1)

        assert self.tracker.is_rate_limited("claude")

        # Manually expire the rate limit
        import datetime

        past_time = datetime.datetime.now() - datetime.timedelta(minutes=1)
        self.tracker._rate_limit_reset_time["claude"] = past_time

        # get_status should clean up expired limits
        status = self.tracker.get_status()
        assert status.get("claude", False) is False

    @pytest.mark.unit
    def test_unknown_provider_not_rate_limited(self):
        """Test that unknown providers are not considered rate limited."""
        assert not self.tracker.is_rate_limited("unknown_provider")

    @pytest.mark.unit
    def test_rate_limit_reset_time_tracking(self):
        """Test that reset times are properly tracked."""
        import datetime

        before_time = datetime.datetime.now()
        self.tracker.set_rate_limited("claude", reset_minutes=60)
        after_time = datetime.datetime.now() + datetime.timedelta(minutes=60)

        # Check that reset time is stored and reasonable
        reset_time = self.tracker._rate_limit_reset_time["claude"]
        assert before_time < reset_time < after_time

    @pytest.mark.unit
    def test_global_rate_limit_status_function(self):
        """Test the global get_rate_limit_status function."""
        # This tests the module-level function that uses the global tracker
        from backend.core.llm_chain import rate_limit_tracker

        # Clear any existing state
        rate_limit_tracker.clear_rate_limit("claude")
        rate_limit_tracker.clear_rate_limit("gemini")

        # Test initial state
        status = get_rate_limit_status()
        assert isinstance(status, dict)

        # Set a rate limit and test
        rate_limit_tracker.set_rate_limited("claude", reset_minutes=60)
        status = get_rate_limit_status()
        assert status.get("claude", False) is True

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "error_message,expected",
        [
            ("Rate limit exceeded", True),
            ("rate limit", True),
            ("RATE_LIMIT_ERROR", True),
            ("429 Too Many Requests", True),
            ("quota exceeded", True),
            ("Normal error message", False),
            ("Connection timeout", False),
            ("Invalid API key", False),
            ("", False),
        ],
    )
    def test_is_rate_limit_error_detection(self, error_message, expected):
        """Test rate limit error detection with various error messages."""

        class MockError(Exception):
            def __init__(self, message):
                self.message = message
                super().__init__(message)

            def __str__(self):
                return self.message

        error = MockError(error_message)
        result = is_rate_limit_error(error)
        assert result == expected

    @pytest.mark.unit
    def test_is_rate_limit_error_with_nested_exceptions(self):
        """Test rate limit error detection with nested exception attributes."""

        class MockError(Exception):
            def __init__(self, message, status_code=None):
                self.message = message
                self.status_code = status_code
                super().__init__(message)

        # Test with status code 429
        error_429 = MockError("Some error", status_code=429)
        assert is_rate_limit_error(error_429) is True

        # Test with other status codes
        error_500 = MockError("Some error", status_code=500)
        assert is_rate_limit_error(error_500) is False
