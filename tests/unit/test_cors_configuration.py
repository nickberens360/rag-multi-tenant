"""
Unit tests for CORS configuration.
Tests that CORS origins are properly configured and validated.
"""

import os
from unittest.mock import patch

from backend.core.config_v2 import AppConfig


class TestCORSConfiguration:
    """Test CORS configuration functionality."""

    def test_get_cors_origins_from_environment(self):
        """Test CORS origins are read from environment variable."""
        test_origins = "http://localhost:3000,https://example.com,http://localhost:4321"

        with patch.dict(os.environ, {"CORS_ORIGINS": test_origins}):
            origins = AppConfig.get_cors_origins()

            expected_origins = ["http://localhost:3000", "https://example.com", "http://localhost:4321"]
            assert origins == expected_origins

    def test_get_cors_origins_invalid_filtered_out(self):
        """Test that invalid CORS origins are filtered out."""
        test_origins = "http://localhost:3000,invalid-url,https://example.com,ftp://badprotocol.com"

        with patch.dict(os.environ, {"CORS_ORIGINS": test_origins}):
            origins = AppConfig.get_cors_origins()

            # Only valid HTTP/HTTPS origins should remain
            expected_origins = ["http://localhost:3000", "https://example.com"]
            assert origins == expected_origins

    def test_get_cors_origins_default_fallback(self):
        """Test CORS origins fallback to defaults when env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            origins = AppConfig.get_cors_origins()

            # Should return default origins (localhost variants)
            assert isinstance(origins, list)
            assert len(origins) > 0
            # Default should include localhost variants
            localhost_found = any("localhost" in origin for origin in origins)
            assert localhost_found

    def test_cors_origin_validation(self):
        """Test individual CORS origin validation."""
        valid_origins = [
            "http://localhost:3000",
            "https://example.com",
            "https://subdomain.example.com:8080",
            "http://192.168.1.1:3000",
        ]

        invalid_origins = [
            "ftp://example.com",  # Invalid protocol
            "localhost:3000",  # Missing protocol
            "https://",  # Invalid format
            "",  # Empty string
            "javascript:alert(1)",  # Dangerous protocol
        ]

        for origin in valid_origins:
            assert AppConfig._is_valid_origin(origin), f"Valid origin rejected: {origin}"

        for origin in invalid_origins:
            assert not AppConfig._is_valid_origin(origin), f"Invalid origin accepted: {origin}"

    def test_cors_wildcard_development_mode(self):
        """Test that wildcard CORS is allowed in development mode."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert AppConfig._is_valid_origin("*")

    def test_cors_wildcard_production_mode(self):
        """Test that wildcard CORS is rejected in production mode."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert not AppConfig._is_valid_origin("*")
