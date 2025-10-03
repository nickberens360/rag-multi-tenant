"""
Unit tests for security settings integration.
Tests that security settings properly control backend behavior.
"""

from unittest.mock import Mock, patch

from backend.core.admin_auth import AdminAuthManager
from backend.core.settings_schemas import SecuritySettings


class TestSecuritySettingsIntegration:
    """Test security settings integration across backend services."""

    def test_dynamic_session_timeout(self):
        """Test that session timeout uses security settings."""
        mock_settings_manager = Mock()
        mock_security_settings = SecuritySettings(session_timeout=7200)  # 2 hours
        mock_settings_manager.get_security_settings.return_value = mock_security_settings

        with patch("backend.core.admin_auth.get_settings_manager", return_value=mock_settings_manager):
            auth = AdminAuthManager()
            timeout_hours = auth.get_dynamic_session_timeout_hours()

            assert timeout_hours == 2  # 7200 seconds = 2 hours
            mock_settings_manager.get_security_settings.assert_called_once()

    def test_dynamic_max_login_attempts(self):
        """Test that max login attempts uses security settings."""
        mock_settings_manager = Mock()
        mock_security_settings = SecuritySettings(max_login_attempts=10)
        mock_settings_manager.get_security_settings.return_value = mock_security_settings

        with patch("backend.core.admin_auth.get_settings_manager", return_value=mock_settings_manager):
            auth = AdminAuthManager()
            max_attempts = auth.get_dynamic_max_login_attempts()

            assert max_attempts == 10
            mock_settings_manager.get_security_settings.assert_called_once()

    def test_dynamic_lockout_duration(self):
        """Test that lockout duration uses security settings."""
        mock_settings_manager = Mock()
        mock_security_settings = SecuritySettings(lockout_duration=600)  # 10 minutes
        mock_settings_manager.get_security_settings.return_value = mock_security_settings

        with patch("backend.core.admin_auth.get_settings_manager", return_value=mock_settings_manager):
            auth = AdminAuthManager()
            lockout_minutes = auth.get_dynamic_lockout_duration_minutes()

            assert lockout_minutes == 10  # 600 seconds = 10 minutes
            mock_settings_manager.get_security_settings.assert_called_once()

    def test_security_settings_fallback_on_error(self):
        """Test that security settings fall back to defaults on error."""
        mock_settings_manager = Mock()
        mock_settings_manager.get_security_settings.side_effect = Exception("Database error")

        with patch("backend.core.admin_auth.get_settings_manager", return_value=mock_settings_manager):
            auth = AdminAuthManager()

            # Should fall back to defaults
            timeout_hours = auth.get_dynamic_session_timeout_hours()
            max_attempts = auth.get_dynamic_max_login_attempts()
            lockout_minutes = auth.get_dynamic_lockout_duration_minutes()

            assert timeout_hours == 24  # Default
            assert max_attempts == 5  # Default
            assert lockout_minutes == 5  # Default

    def test_rate_limiting_settings_validation(self):
        """Test that rate limiting settings are properly validated."""
        # Test valid settings
        settings = SecuritySettings(rate_limit_requests=200, rate_limit_window=120)
        assert settings.rate_limit_requests == 200
        assert settings.rate_limit_window == 120

        # Test validation through from_dict
        data = {
            "rate_limit_requests": 5000,  # Within bounds
            "rate_limit_window": 30,  # Within bounds
            "enable_rate_limiting": True,
        }
        validated = SecuritySettings.from_dict(data)
        assert validated.rate_limit_requests == 5000
        assert validated.rate_limit_window == 30
        assert validated.enable_rate_limiting is True

    def test_session_timeout_bounds_validation(self):
        """Test that session timeout is within valid bounds."""
        # Test minimum bound
        data = {"session_timeout": 100}  # Below minimum (300)
        settings = SecuritySettings.from_dict(data)
        assert settings.session_timeout == 300  # Should be clamped to minimum

        # Test maximum bound
        data = {"session_timeout": 1000000}  # Above maximum (604800)
        settings = SecuritySettings.from_dict(data)
        assert settings.session_timeout == 604800  # Should be clamped to maximum

        # Test valid value
        data = {"session_timeout": 3600}  # 1 hour - valid
        settings = SecuritySettings.from_dict(data)
        assert settings.session_timeout == 3600

    def test_login_attempts_bounds_validation(self):
        """Test that max login attempts is within valid bounds."""
        # Test minimum bound
        data = {"max_login_attempts": 0}  # Below minimum (1)
        settings = SecuritySettings.from_dict(data)
        assert settings.max_login_attempts == 1  # Should be clamped to minimum

        # Test maximum bound
        data = {"max_login_attempts": 200}  # Above maximum (100)
        settings = SecuritySettings.from_dict(data)
        assert settings.max_login_attempts == 100  # Should be clamped to maximum

        # Test valid value
        data = {"max_login_attempts": 10}  # Valid
        settings = SecuritySettings.from_dict(data)
        assert settings.max_login_attempts == 10

    def test_lockout_duration_bounds_validation(self):
        """Test that lockout duration is within valid bounds."""
        # Test minimum bound
        data = {"lockout_duration": 30}  # Below minimum (60)
        settings = SecuritySettings.from_dict(data)
        assert settings.lockout_duration == 60  # Should be clamped to minimum

        # Test maximum bound
        data = {"lockout_duration": 100000}  # Above maximum (86400)
        settings = SecuritySettings.from_dict(data)
        assert settings.lockout_duration == 86400  # Should be clamped to maximum

        # Test valid value
        data = {"lockout_duration": 600}  # 10 minutes - valid
        settings = SecuritySettings.from_dict(data)
        assert settings.lockout_duration == 600

    def test_rate_limit_requests_bounds_validation(self):
        """Test that rate limit requests is within valid bounds."""
        # Test minimum bound
        data = {"rate_limit_requests": 0}  # Below minimum (1)
        settings = SecuritySettings.from_dict(data)
        assert settings.rate_limit_requests == 1  # Should be clamped to minimum

        # Test maximum bound
        data = {"rate_limit_requests": 15000}  # Above maximum (10000)
        settings = SecuritySettings.from_dict(data)
        assert settings.rate_limit_requests == 10000  # Should be clamped to maximum

        # Test valid value
        data = {"rate_limit_requests": 500}  # Valid
        settings = SecuritySettings.from_dict(data)
        assert settings.rate_limit_requests == 500

    def test_rate_limit_window_bounds_validation(self):
        """Test that rate limit window is within valid bounds."""
        # Test minimum bound
        data = {"rate_limit_window": 0}  # Below minimum (1)
        settings = SecuritySettings.from_dict(data)
        assert settings.rate_limit_window == 1  # Should be clamped to minimum

        # Test maximum bound
        data = {"rate_limit_window": 5000}  # Above maximum (3600)
        settings = SecuritySettings.from_dict(data)
        assert settings.rate_limit_window == 3600  # Should be clamped to maximum

        # Test valid value
        data = {"rate_limit_window": 120}  # 2 minutes - valid
        settings = SecuritySettings.from_dict(data)
        assert settings.rate_limit_window == 120

    def test_boolean_fields_validation(self):
        """Test that boolean fields are properly validated."""
        # Test string to boolean conversion
        data = {
            "enable_analytics": "true",
            "enable_query_logging": "false",
            "require_https": "True",
            "enable_rate_limiting": "FALSE",
        }
        settings = SecuritySettings.from_dict(data)

        assert settings.enable_analytics is True
        assert settings.enable_query_logging is False
        assert settings.require_https is True
        assert settings.enable_rate_limiting is False

    def test_security_settings_json_serialization(self):
        """Test that security settings can be serialized to/from JSON."""
        settings = SecuritySettings(
            enable_analytics=True,
            enable_query_logging=True,
            enable_rate_limiting=True,
            rate_limit_requests=50,
            rate_limit_window=30,
            session_timeout=1800,  # 30 minutes
            max_login_attempts=3,
            lockout_duration=900,  # 15 minutes
            low_similarity_threshold=0.6,
        )

        # Test serialization
        json_str = settings.to_json()
        assert isinstance(json_str, str)

        # Test deserialization
        loaded_settings = SecuritySettings.from_json(json_str)
        assert loaded_settings.enable_analytics is True
        assert loaded_settings.enable_query_logging is True
        assert loaded_settings.enable_rate_limiting is True
        assert loaded_settings.rate_limit_requests == 50
        assert loaded_settings.rate_limit_window == 30
        assert loaded_settings.session_timeout == 1800
        assert loaded_settings.max_login_attempts == 3
        assert loaded_settings.lockout_duration == 900
        assert loaded_settings.low_similarity_threshold == 0.6

    def test_consolidated_monitoring_settings(self):
        """Test that monitoring settings consolidated from FeatureFlags work correctly."""
        # Test analytics and monitoring settings
        data = {
            "enable_analytics": True,
            "enable_query_logging": True,
            "enable_audit_logging": True,
            "enable_rate_limiting": True,
            "low_similarity_threshold": 0.8,
        }

        settings = SecuritySettings.from_dict(data)

        assert settings.enable_analytics is True
        assert settings.enable_query_logging is True
        assert settings.enable_audit_logging is True
        assert settings.enable_rate_limiting is True
        assert settings.low_similarity_threshold == 0.8

        # Test bounds validation for low_similarity_threshold
        data_out_of_bounds = {
            "low_similarity_threshold": 1.5,  # Above maximum (1.0)
        }

        settings_bounded = SecuritySettings.from_dict(data_out_of_bounds)
        assert settings_bounded.low_similarity_threshold == 1.0  # Clamped to maximum

        data_below_bounds = {
            "low_similarity_threshold": -0.1,  # Below minimum (0.0)
        }

        settings_bounded_low = SecuritySettings.from_dict(data_below_bounds)
        assert settings_bounded_low.low_similarity_threshold == 0.0  # Clamped to minimum
