"""
Tests for admin diagnostics integration with feature flag control.

Verifies that the diagnostics router is properly integrated behind a feature flag
and that the system behaves correctly with zero behavior change when disabled.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.app_factory import create_app


class TestDiagnosticsIntegration:
    """Test diagnostics router integration with feature flag control."""

    def test_diagnostics_disabled_by_default(self):
        """Test that diagnostics endpoints are not available when feature flag is disabled (default)."""
        # Create app with default settings (diagnostics disabled)
        with patch("backend.core.app_factory.get_settings_manager") as mock_settings_manager:
            mock_manager = Mock()
            mock_manager.is_feature_enabled.return_value = False  # Feature disabled
            mock_settings_manager.return_value = mock_manager

            app = create_app()
            client = TestClient(app)

            # Try to access diagnostics endpoints - should return 404
            response = client.get("/api/admin/diagnostics/config-status")
            assert response.status_code == 404

            response = client.get("/api/admin/diagnostics/env-only-status")
            assert response.status_code == 404

            response = client.get("/api/admin/diagnostics/admin-managed-status")
            assert response.status_code == 404

            response = client.get("/api/admin/diagnostics/config-validation")
            assert response.status_code == 404

    def test_diagnostics_enabled_with_feature_flag(self):
        """Test that diagnostics endpoints are available when feature flag is enabled."""

        # Mock authentication dependency
        def mock_auth():
            return {"user_id": "admin", "role": "admin"}

        with (
            patch("backend.core.app_factory.get_settings_manager") as mock_app_settings,
            patch("backend.routes.admin_diagnostics.get_settings_manager") as mock_diagnostics_settings,
        ):

            # Enable diagnostics feature flag in app factory
            mock_app_manager = Mock()
            mock_app_manager.is_feature_enabled.return_value = True  # Feature enabled
            mock_app_settings.return_value = mock_app_manager

            # Mock diagnostics settings manager
            mock_diag_manager = Mock()
            mock_diagnostics_settings.return_value = mock_diag_manager

            app = create_app()

            # Override auth dependency
            from backend.core.admin_auth import require_admin_auth

            app.dependency_overrides[require_admin_auth] = mock_auth

            client = TestClient(app)

            # Diagnostics endpoints should now be available (may return errors due to mocking, but should route)
            response = client.get("/api/admin/diagnostics/config-status")
            assert response.status_code != 404  # Should route to endpoint

    def test_feature_flag_check_failure_graceful_degradation(self):
        """Test graceful degradation when feature flag check fails."""
        with patch("backend.core.app_factory.get_settings_manager") as mock_settings_manager:
            # Simulate settings manager failure
            mock_settings_manager.side_effect = Exception("Settings manager unavailable")

            # App should still start successfully, just without diagnostics
            app = create_app()
            client = TestClient(app)

            # Diagnostics should not be available due to failed feature flag check
            response = client.get("/api/admin/diagnostics/config-status")
            assert response.status_code == 404

            # Other admin endpoints should still work
            response = client.get("/api/admin/ping")
            assert response.status_code == 200

    def test_zero_behavior_change_with_disabled_flag(self):
        """Test that disabling diagnostics has zero impact on existing functionality."""
        with patch("backend.core.app_factory.get_settings_manager") as mock_settings_manager:
            mock_manager = Mock()
            mock_manager.is_feature_enabled.return_value = False  # Diagnostics disabled
            mock_settings_manager.return_value = mock_manager

            app = create_app()
            client = TestClient(app)

            # Existing admin endpoints should work normally
            response = client.get("/api/admin/ping")
            assert response.status_code == 200

            # Public endpoints should work normally
            response = client.get("/api/health")
            assert response.status_code == 200

            # Only diagnostics endpoints should be unavailable
            response = client.get("/api/admin/diagnostics/config-status")
            assert response.status_code == 404

    def test_settings_manager_feature_flag_method(self):
        """Test that the settings manager can check feature flags."""
        from backend.core.settings_manager import SettingsManager

        # Test with mocked feature flags object
        with patch("backend.core.settings_manager.admin_db_manager") as mock_db:
            # Create a real FeatureFlags instance for proper testing
            from backend.core.settings_schemas import FeatureFlags

            feature_flags = FeatureFlags()
            feature_flags.enable_admin_diagnostics = True

            # Mock the database to return our feature flags as JSON
            import json

            mock_db.get_admin_setting.return_value = json.dumps(feature_flags.to_dict())

            settings_manager = SettingsManager()
            result = settings_manager.is_feature_enabled("enable_admin_diagnostics")

            # Should return True when flag is enabled
            assert result is True

    def test_app_includes_diagnostics_import(self):
        """Test that the app factory properly imports admin_diagnostics."""
        # This test ensures the import doesn't cause any import errors
        try:
            from backend.routes import admin_diagnostics

            assert hasattr(admin_diagnostics, "router")
        except ImportError as e:
            pytest.fail(f"admin_diagnostics import failed: {e}")

    def test_feature_flag_schema_includes_diagnostics(self):
        """Test that FeatureFlags schema includes enable_admin_diagnostics."""
        from backend.core.settings_schemas import FeatureFlags

        # Create instance and check field exists
        flags = FeatureFlags()
        assert hasattr(flags, "enable_admin_diagnostics")
        assert flags.enable_admin_diagnostics is False  # Default should be False

        # Test serialization includes the field
        flag_dict = flags.to_dict()
        assert "enable_admin_diagnostics" in flag_dict
        assert flag_dict["enable_admin_diagnostics"] is False


class TestConfigurationValidation:
    """Test configuration validation functionality."""

    def test_configuration_validator_import(self):
        """Test that configuration validation can be imported."""
        try:
            from backend.core.config_validation import ConfigurationValidator

            # Test basic instantiation
            validator = ConfigurationValidator()
            assert validator is not None

        except ImportError as e:
            pytest.fail(f"config_validation import failed: {e}")

    def test_critical_settings_validation(self):
        """Test critical settings validation functionality."""
        from backend.core.config_validation import validate_critical_settings

        with patch.dict("os.environ", {}, clear=True):
            # No environment variables set
            result = validate_critical_settings()

            assert "critical_missing" in result
            assert "overall_status" in result
            assert result["overall_status"] == "critical"  # Should be critical without API keys

    def test_health_summary_structure(self):
        """Test that health summary returns expected structure."""
        from backend.core.config_validation import get_configuration_health_summary

        with patch("backend.core.config_validation.get_settings_manager") as mock_settings:
            mock_manager = Mock()
            mock_manager.get_feature_flags.return_value = None
            mock_manager.get_core_settings.return_value = None
            mock_manager.get_response_settings.return_value = None
            mock_settings.return_value = mock_manager

            result = get_configuration_health_summary()

            # Check expected structure
            assert "overall_health" in result
            assert "critical_settings" in result
            assert "feature_flags" in result
            assert "summary" in result
            assert "recommendations" in result
            assert "validation_timestamp" in result

    def test_new_diagnostics_endpoints_with_validation(self):
        """Test that new validation endpoints are properly structured."""

        def mock_auth():
            return {"user_id": "admin", "role": "admin"}

        with (
            patch("backend.core.app_factory.get_settings_manager") as mock_app_settings,
            patch("backend.routes.admin_diagnostics.get_configuration_health_summary") as mock_health,
            patch("backend.routes.admin_diagnostics.validate_critical_settings") as mock_critical,
        ):

            # Enable diagnostics feature flag
            mock_app_manager = Mock()
            mock_app_manager.is_feature_enabled.return_value = True
            mock_app_settings.return_value = mock_app_manager

            # Mock validation responses with complete structure
            mock_health.return_value = {
                "overall_health": "healthy",
                "critical_settings": {"overall_status": "healthy"},
                "feature_flags": {"overall_status": "healthy"},
                "summary": {"total_issues": 0},
                "recommendations": [],
                "validation_timestamp": "2024-01-01T00:00:00Z",
            }
            mock_critical.return_value = {
                "overall_status": "healthy",
                "critical_missing": [],
                "warnings": [],
                "recommendations": ["Configuration is optimal"],
                "validation_timestamp": "2024-01-01T00:00:00Z",
            }

            app = create_app()

            # Override auth dependency
            from backend.core.admin_auth import require_admin_auth

            app.dependency_overrides[require_admin_auth] = mock_auth

            client = TestClient(app)

            # Test new validation endpoints
            response = client.get("/api/admin/diagnostics/config-validation")
            assert response.status_code == 200
            data = response.json()
            assert "validation_results" in data
            assert "timestamp" in data

            response = client.get("/api/admin/diagnostics/critical-settings-check")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "critical_missing" in data
            assert "critical_count" in data
