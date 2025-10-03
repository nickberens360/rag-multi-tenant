"""Tests for core.config module."""

import os
from unittest.mock import patch

import pytest

from backend.core.config_v2 import AppConfig


class TestConfig:
    """Test cases for configuration module."""

    @pytest.mark.unit
    def test_default_llm_configuration(self):
        """Test default LLM configuration values."""
        assert AppConfig.get_primary_llm() == "claude"
        assert "claude" in AppConfig.get_claude_model()
        assert "gemini" in AppConfig.get_gemini_model()
        assert "embedding" in AppConfig.get_embedding_model()

    @pytest.mark.unit
    def test_search_threshold_validation(self):
        """Test search threshold validation with valid values."""
        assert 0 <= AppConfig.get_search_threshold() <= 100
        assert isinstance(AppConfig.get_search_threshold(), int)

    @pytest.mark.unit
    def test_max_results_validation(self):
        """Test max results validation with valid values."""
        assert 1 <= AppConfig.get_max_results() <= 100
        assert isinstance(AppConfig.get_max_results(), int)

    @pytest.mark.unit
    def test_port_validation(self):
        """Test port validation with valid values."""
        assert 1024 <= AppConfig.PORT <= 65535
        assert isinstance(AppConfig.PORT, int)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "origin,expected",
        [
            ("https://example.com", True),
            ("http://localhost:3000", True),
            ("http://127.0.0.1:8080", True),
            ("https://nickberens.me", True),
            ("*", True),  # In development mode
            ("invalid-url", False),
            ("ftp://example.com", False),
            ("http://malware.evil.com", False),
            ("", False),
            (None, False),
        ],
    )
    def test_cors_origin_validation(self, origin, expected):
        """Test CORS origin validation with various inputs."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            result = AppConfig._is_valid_origin(origin)
            assert result == expected

    @pytest.mark.unit
    def test_cors_wildcard_blocked_in_production(self):
        """Test that wildcard CORS origin is blocked in production."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            result = AppConfig._is_valid_origin("*")
            assert result is False

    @pytest.mark.unit
    def test_cors_https_required_for_production_domains(self):
        """Test that HTTPS is required for production domains."""
        # Non-localhost domains should require HTTPS
        result = AppConfig._is_valid_origin("http://example.com")
        assert result is False

        result = AppConfig._is_valid_origin("https://example.com")
        assert result is True

    @pytest.mark.unit
    def test_cors_localhost_allows_http(self):
        """Test that localhost allows HTTP connections."""
        localhost_origins = ["http://localhost:3000", "http://127.0.0.1:8080", "https://localhost:4321"]

        for origin in localhost_origins:
            result = AppConfig._is_valid_origin(origin)
            assert result is True, f"Should allow {origin}"

    @pytest.mark.unit
    def test_get_cors_origins_from_environment(self):
        """Test CORS origins retrieval from environment variable."""
        test_origins = "https://example.com,http://localhost:3000,https://test.com"

        with patch.dict(os.environ, {"CORS_ORIGINS": test_origins}):
            origins = AppConfig.get_cors_origins()

            assert "https://example.com" in origins
            assert "http://localhost:3000" in origins
            assert "https://test.com" in origins

    @pytest.mark.unit
    def test_get_cors_origins_filters_invalid(self):
        """Test that invalid CORS origins are filtered out."""
        test_origins = "https://valid.com,invalid-url,ftp://invalid.com"

        with patch.dict(os.environ, {"CORS_ORIGINS": test_origins}):
            origins = AppConfig.get_cors_origins()

            assert "https://valid.com" in origins
            assert "invalid-url" not in origins
            assert "ftp://invalid.com" not in origins

    @pytest.mark.unit
    def test_get_cors_origins_production_defaults(self):
        """Test default CORS origins in production environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            origins = AppConfig.get_cors_origins()

            # Should include production domains
            assert any("nickberens.me" in origin for origin in origins)
            assert any("netlify.app" in origin for origin in origins)

            # Should not include localhost in production defaults
            localhost_origins = [origin for origin in origins if "localhost" in origin]
            assert len(localhost_origins) == 0

    @pytest.mark.unit
    def test_get_cors_origins_development_defaults(self):
        """Test default CORS origins in development environment."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            origins = AppConfig.get_cors_origins()

            # Should include both production and development domains
            assert any("nickberens.me" in origin for origin in origins)
            assert any("localhost" in origin for origin in origins)

    @pytest.mark.unit
    def test_suspicious_domain_blocking(self):
        """Test that suspicious domains are blocked."""
        suspicious_domains = [
            "https://malware.com",
            "https://phishing.evil.com",
            "https://hack.test.com",
            "https://exploit.example.com",
        ]

        for domain in suspicious_domains:
            result = AppConfig._is_valid_origin(domain)
            assert result is False, f"Should block suspicious domain: {domain}"

    @pytest.mark.unit
    def test_domain_format_validation(self):
        """Test domain format validation."""
        invalid_domains = ["https://", "https://.com", "https://com.", "https://..com", "https://domain..com"]

        for domain in invalid_domains:
            result = AppConfig._is_valid_origin(domain)
            assert result is False, f"Should reject invalid domain format: {domain}"

    @pytest.mark.unit
    def test_rate_limit_configuration(self):
        """Test rate limit configuration."""
        assert AppConfig.get_rate_limit() is not None
        assert isinstance(AppConfig.get_rate_limit(), str)
        assert "/" in AppConfig.get_rate_limit()  # Should be in format like "5/minute"

    @pytest.mark.unit
    def test_app_metadata(self):
        """Test application metadata configuration."""
        assert AppConfig.APP_TITLE is not None
        assert AppConfig.APP_DESCRIPTION is not None
        assert AppConfig.APP_VERSION is not None

        assert isinstance(AppConfig.APP_TITLE, str)
        assert isinstance(AppConfig.APP_DESCRIPTION, str)
        assert isinstance(AppConfig.APP_VERSION, str)

    @pytest.mark.unit
    def test_default_search_threshold_is_valid(self):
        """Search threshold should be a valid percentage (0-100)."""
        assert 0 <= AppConfig.get_search_threshold() <= 100
        assert isinstance(AppConfig.get_search_threshold(), int)

    @pytest.mark.unit
    def test_default_max_results_is_valid_range(self):
        """Max results should be in valid range (1-100)."""
        max_results = AppConfig.get_max_results()
        assert 1 <= max_results <= 100
        assert isinstance(max_results, int)

    @pytest.mark.unit
    def test_default_port_is_8000(self):
        """Default port is 8000 (code default)."""
        assert AppConfig.PORT == 8000
