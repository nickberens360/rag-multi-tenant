def test_response_settings_roundtrip_and_bounds():
    from backend.core.settings_schemas import ResponseSettings

    bad = {
        "max_context_length": "not-an-int",
        "max_context_documents": "999",
        "context_fill_ratio": "2.5",
        "cache_ttl_seconds": -10,
        "response_cache_ttl_seconds": "15",
        "response_llm": "unknown",
        "response_claude_model": "bogus",
        "response_gemini_model": "bogus",
        "enable_caching": "true",
        "enable_markdown": "False",
    }

    s = ResponseSettings.from_dict(bad)
    assert 100 <= s.max_context_length <= 10000
    assert 1 <= s.max_context_documents <= 10
    assert 0.1 <= s.context_fill_ratio <= 1.0
    assert 60 <= s.cache_ttl_seconds <= 86400
    assert 60 <= s.response_cache_ttl_seconds <= 86400
    assert s.response_llm in ("claude", "gemini")
    assert isinstance(s.enable_caching, bool)
    assert isinstance(s.enable_markdown, bool)

    # round‑trip JSON
    s2 = ResponseSettings.from_json(s.to_json())
    assert s2 == s


def test_security_settings_validation_and_bounds():
    from backend.core.settings_schemas import SecuritySettings

    bad = {
        "excluded_ips": ["127.0.0.1", "not-an-ip", ""],
        "rate_limit_requests": "999999",
        "rate_limit_window": 0,
        "max_login_attempts": -1,
        "lockout_duration": "30",
        "enable_rate_limiting": "false",
    }

    s = SecuritySettings.from_dict(bad)
    assert s.excluded_ips == ["127.0.0.1"]
    assert 1 <= s.rate_limit_requests <= 10000
    assert 1 <= s.rate_limit_window <= 3600
    assert 1 <= s.max_login_attempts <= 100
    assert 60 <= s.lockout_duration <= 86400
    assert s.enable_rate_limiting is False

    # round‑trip
    s2 = SecuritySettings.from_json(s.to_json())
    assert s2 == s


def test_query_routing_settings_coercion_and_clamps():
    from backend.core.settings_schemas import QueryRoutingSettings

    bad = {
        "enable_smart_routing": "false",
        "enable_fuzzy_matching": "True",
        "similarity_threshold": "-1",
        "fuzzy_threshold": 2.0,
        "query_cache_ttl_seconds": "10",
        "cache_ttl_seconds": "999999",
        "max_retries": "50",
        "max_search_results": "0",
        "fallback_strategy": "not-valid",
    }

    s = QueryRoutingSettings.from_dict(bad)
    assert s.enable_smart_routing is False
    assert s.enable_fuzzy_matching is True
    assert 0.0 <= s.similarity_threshold <= 1.0
    assert 0.0 <= s.fuzzy_threshold <= 1.0
    assert 60 <= s.query_cache_ttl_seconds <= 3600
    assert 60 <= s.cache_ttl_seconds <= 3600
    assert 0 <= s.max_retries <= 10
    assert 1 <= s.max_search_results <= 100
    assert s.fallback_strategy in {
        "comprehensive_search",
        "semantic_similarity",
        "keyword_matching",
        "default_response",
    }


def test_system_configuration_settings_llm_and_rate_limit():
    from backend.core.settings_schemas import SystemConfigurationSettings

    bad = {
        "response_llm": "nope",
        "processing_llm": "nope",
        "response_claude_model": "bad-model",
        "response_gemini_model": "bad-model",
        "processing_claude_model": "bad-model",
        "processing_gemini_model": "bad-model",
        "system_cache_ttl_seconds": "-5",
        "max_cache_size": "500000",
        "rate_limit": "abc/min",
    }

    s = SystemConfigurationSettings.from_dict(bad)
    assert s.response_llm in ("claude", "gemini")
    assert s.processing_llm in ("claude_haiku", "claude", "gemini")
    assert isinstance(s.system_cache_ttl_seconds, int) and 60 <= s.system_cache_ttl_seconds <= 86400
    assert isinstance(s.max_cache_size, int) and 10 <= s.max_cache_size <= 10000
    # Invalid rate strings should default to the class default
    assert isinstance(s.rate_limit, str) and "/" in s.rate_limit
