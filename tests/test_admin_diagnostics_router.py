"""
Tests for the admin diagnostics router.

Verifies that the configuration diagnostics endpoints work correctly
without exposing sensitive information.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.routes.admin_diagnostics import (
    _check_admin_managed_env_settings,
    _check_database_settings,
    _check_env_only_settings,
    _generate_summary,
    router,
)


class TestAdminDiagnosticsRouter:
    """Test the admin diagnostics router endpoints."""

    def test_check_env_only_settings(self):
        """Test environment-only settings check."""
        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "test-key", "ENVIRONMENT": "development", "DEBUG_MODE": "false"},
            clear=True,
        ):
            result = _check_env_only_settings()

            # Check that we detect configured settings
            assert result["ANTHROPIC_API_KEY"]["present"] is True
            assert result["ANTHROPIC_API_KEY"]["classification"] == "env-only"
            assert "Claude API authentication" in result["ANTHROPIC_API_KEY"]["description"]

            # Check that we detect missing settings
            assert result["GOOGLE_API_KEY"]["present"] is False

            # Verify safe exposure of non-sensitive values
            assert result["ENVIRONMENT"]["current_value"] == "development"
            assert result["DEBUG_MODE"]["current_value"] == "false"

    def test_check_admin_managed_env_settings(self):
        """Test admin-managed environment settings check."""
        with patch.dict("os.environ", {"PRIMARY_LLM": "claude", "ENABLE_CACHING": "true"}, clear=True):
            result = _check_admin_managed_env_settings()

            # Check configured settings
            assert result["PRIMARY_LLM"]["present"] is True
            assert result["PRIMARY_LLM"]["classification"] == "admin-managed"
            assert result["PRIMARY_LLM"]["override_available"] is True

            # Check missing settings
            assert result["GEMINI_MODEL"]["present"] is False

    def test_check_database_settings(self):
        """Test database settings check."""
        # Mock settings manager
        mock_settings_manager = Mock()
        mock_settings_manager.get_followup_settings.return_value = Mock()  # Configured
        mock_settings_manager.get_response_settings.return_value = None  # Not configured

        with patch("backend.routes.admin_diagnostics.get_settings_manager", return_value=mock_settings_manager):
            result = _check_database_settings()

            assert len(result) > 0
            assert "followup_settings" in result
            assert result["followup_settings"]["configured"] is True
            assert result["followup_settings"]["classification"] == "admin-managed"
            assert result["followup_settings"]["field_count"] == 9

    def test_generate_summary(self):
        """Test summary generation."""
        env_only = {
            "KEY1": {"present": True},
            "KEY2": {"present": False},
        }
        admin_managed_env = {
            "KEY3": {"present": True},
            "KEY4": {"present": True},
            "KEY5": {"present": False},
        }
        database_settings = {
            "cat1": {"configured": True},
            "cat2": {"configured": False},
        }

        summary = _generate_summary(env_only, admin_managed_env, database_settings)

        assert summary["env_only"]["total"] == 2
        assert summary["env_only"]["configured"] == 1
        assert summary["env_only"]["percentage_configured"] == 50.0

        assert summary["admin_managed_env"]["total"] == 3
        assert summary["admin_managed_env"]["configured"] == 2
        assert summary["admin_managed_env"]["percentage_configured"] == 66.7

        assert summary["database_settings"]["total_categories"] == 2
        assert summary["database_settings"]["configured_categories"] == 1

    def test_setting_descriptions(self):
        """Test that setting descriptions are informative."""
        from backend.routes.admin_diagnostics import _get_setting_description

        # Test known descriptions
        assert "Claude API" in _get_setting_description("ANTHROPIC_API_KEY")
        assert "environment" in _get_setting_description("ENVIRONMENT").lower()

        # Test fallback for unknown setting
        desc = _get_setting_description("UNKNOWN_SETTING")
        assert "UNKNOWN_SETTING" in desc


class TestDiagnosticsEndpoints:
    """Test diagnostics endpoints with mocked authentication."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked auth."""
        from fastapi import FastAPI

        from backend.core.admin_auth import require_admin_auth

        app = FastAPI()

        # Mock authentication dependency
        def mock_auth():
            return {"user_id": "admin", "role": "admin"}

        # Override the auth dependency
        app.dependency_overrides[require_admin_auth] = mock_auth

        app.include_router(router, prefix="/admin")

        return TestClient(app)

    def test_config_status_endpoint_structure(self, client):
        """Test config status endpoint returns proper structure."""
        with patch("backend.routes.admin_diagnostics.get_settings_manager"):
            response = client.get("/admin/diagnostics/config-status")

            assert response.status_code == 200
            data = response.json()

            # Check required sections
            assert "env_only" in data
            assert "admin_managed_env" in data
            assert "database_settings" in data
            assert "summary" in data
            assert "timestamp" in data

    def test_env_only_status_endpoint(self, client):
        """Test env-only status endpoint."""
        with patch("backend.routes.admin_diagnostics._check_env_only_settings") as mock_check:
            mock_check.return_value = {"ANTHROPIC_API_KEY": {"present": True, "classification": "env-only"}}

            response = client.get("/admin/diagnostics/env-only-status")

            assert response.status_code == 200
            data = response.json()

            assert "env_only_settings" in data
            assert "summary" in data
            assert "timestamp" in data

    def test_admin_managed_status_endpoint(self, client):
        """Test admin-managed status endpoint."""
        with (
            patch("backend.routes.admin_diagnostics._check_admin_managed_env_settings") as mock_env,
            patch("backend.routes.admin_diagnostics._check_database_settings") as mock_db,
        ):

            mock_env.return_value = {}
            mock_db.return_value = {}

            response = client.get("/admin/diagnostics/admin-managed-status")

            assert response.status_code == 200
            data = response.json()

            assert "admin_managed_env" in data
            assert "database_settings" in data
            assert "summary" in data

    def test_no_secrets_exposed(self, client):
        """Test that no sensitive values are exposed."""
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "secret-key-123"}),
            patch("backend.routes.admin_diagnostics.get_settings_manager"),
        ):

            response = client.get("/admin/diagnostics/config-status")
            data = response.json()

            # Convert entire response to string to check for secrets
            response_str = str(data)

            # Ensure secret values are not in response
            assert "secret-key-123" not in response_str
            assert "ANTHROPIC_API_KEY" in response_str  # Setting name should be present

            # Check that only safe values are exposed
            if "ENVIRONMENT" in data["env_only"]:
                # Environment is safe to expose
                assert "current_value" in data["env_only"]["ENVIRONMENT"]
