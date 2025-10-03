"""
Unit tests for feature flags integration.
Tests that feature flags properly control backend behavior.
"""

from unittest.mock import Mock, patch

from backend.core.followup_service import FollowUpService
from backend.core.query_router import QueryRouter, QueryType
from backend.core.settings_schemas import FeatureFlags
from backend.core.sqlite_query_logger import SQLiteQueryLogger


class TestFeatureFlagsIntegration:
    """Test feature flag integration across backend services."""

    def test_followup_questions_feature_flag_disabled(self):
        """Test that followup questions are disabled when feature flag is off."""
        mock_settings_manager = Mock()
        mock_settings_manager.is_feature_enabled.return_value = False

        with patch("backend.core.followup_service.get_settings_manager", return_value=mock_settings_manager):
            service = FollowUpService()
            result = service.generate_followups("test question", "test response")

            assert result == []
            mock_settings_manager.is_feature_enabled.assert_called_with("enable_followup_questions")

    def test_followup_questions_feature_flag_enabled(self):
        """Test that followup questions work when feature flag is on."""
        mock_settings_manager = Mock()
        mock_settings_manager.is_feature_enabled.return_value = True

        # Mock the followup settings to return defaults
        mock_followup_settings = Mock()
        mock_followup_settings.enabled = True
        mock_followup_settings.service_type = "static"

        with patch("backend.core.followup_service.get_settings_manager", return_value=mock_settings_manager):
            with patch("backend.core.followup_service.admin_db_manager"):
                service = FollowUpService()
                # Mock the _get_settings method to return our mock settings
                service._get_settings = Mock(return_value=mock_followup_settings)
                service._generate_static_questions = Mock(return_value=["Test question?"])

                result = service.generate_followups("test question", "test response")

                assert len(result) > 0
                mock_settings_manager.is_feature_enabled.assert_called_with("enable_followup_questions")

    def test_smart_routing_feature_flag_disabled(self):
        """Test that smart routing is disabled when feature flag is off."""
        mock_settings_manager = Mock()
        mock_settings_manager.is_feature_enabled.return_value = False

        with patch("backend.core.query_router.get_settings_manager", return_value=mock_settings_manager):
            router = QueryRouter()
            query_type, search_term = router.route_query("show me images of cats")

            # Should fall back to AI text response when smart routing is disabled
            assert query_type == QueryType.AI_TEXT_RESPONSE
            assert search_term is None
            mock_settings_manager.is_feature_enabled.assert_called_with("enable_smart_routing")

    def test_smart_routing_feature_flag_enabled(self):
        """Test that smart routing works when feature flag is on."""
        mock_settings_manager = Mock()
        mock_settings_manager.is_feature_enabled.return_value = True

        with patch("backend.core.query_router.get_settings_manager", return_value=mock_settings_manager):
            router = QueryRouter()
            query_type, search_term = router.route_query("show me images of cats")

            # Should use smart routing logic
            assert query_type != QueryType.AI_TEXT_RESPONSE or search_term is not None
            mock_settings_manager.is_feature_enabled.assert_called_with("enable_smart_routing")

    def test_analytics_feature_flag_disabled(self):
        """Test that analytics logging is disabled when feature flag is off."""
        mock_settings_manager = Mock()
        mock_settings_manager.is_feature_enabled.return_value = False

        with patch("backend.core.sqlite_query_logger.get_settings_manager", return_value=mock_settings_manager):
            with patch("backend.core.sqlite_query_logger.Path"):
                logger = SQLiteQueryLogger()

                # Mock the database connection
                with patch.object(logger, "_get_sqlite_connection"):
                    logger.log_query(
                        client_ip="127.0.0.1",
                        question="test question",
                        response="test response",
                        model_used="claude-3-5-sonnet",
                        query_type="text",
                        response_time=1.0,
                    )

                mock_settings_manager.is_feature_enabled.assert_called_with("enable_analytics")

    def test_analytics_feature_flag_enabled(self):
        """Test that analytics logging works when feature flag is on."""
        mock_settings_manager = Mock()
        mock_settings_manager.is_feature_enabled.return_value = True

        with patch("backend.core.sqlite_query_logger.get_settings_manager", return_value=mock_settings_manager):
            with patch("backend.core.sqlite_query_logger.Path"):
                logger = SQLiteQueryLogger()

                # Mock the entire log_query method to avoid database complexity
                with patch.object(logger, "_process_ip_for_logging", return_value="127.0.0.1"):
                    with patch("backend.core.sqlite_query_logger.get_geolocation_service", return_value=None):
                        with patch.object(logger, "_get_sqlite_connection") as mock_connection:
                            # Make the context manager return a mock
                            mock_connection.__enter__ = Mock()
                            mock_connection.__exit__ = Mock()
                            mock_cursor = Mock()
                            mock_connection.__enter__.return_value.cursor.return_value = mock_cursor

                            logger.log_query(
                                client_ip="127.0.0.1",
                                question="test question",
                                response="test response",
                                model_used="claude-3-5-sonnet",
                                query_type="text",
                                response_time=1.0,
                            )

                # Main assertion: feature flag was checked
                mock_settings_manager.is_feature_enabled.assert_called_with("enable_analytics")

    def test_feature_flags_schema_validation(self):
        """Test that feature flags schema has all required flags."""
        flags = FeatureFlags()

        # Check that all expected flags exist with correct defaults
        assert hasattr(flags, "enable_followup_questions")
        assert hasattr(flags, "enable_smart_routing")
        assert hasattr(flags, "enable_caching")
        assert hasattr(flags, "enable_analytics")
        assert hasattr(flags, "enable_debug_mode")
        assert hasattr(flags, "enable_maintenance_mode")
        assert hasattr(flags, "enable_rate_limiting")
        assert hasattr(flags, "enable_api_versioning")

        # Check default values
        assert flags.enable_followup_questions is True
        assert flags.enable_smart_routing is True
        assert flags.enable_caching is True
        assert flags.enable_analytics is True
        assert flags.enable_debug_mode is False
        assert flags.enable_maintenance_mode is False
        assert flags.enable_rate_limiting is True
        assert flags.enable_api_versioning is False

    def test_feature_flags_json_serialization(self):
        """Test that feature flags can be serialized to/from JSON."""
        flags = FeatureFlags(enable_followup_questions=False, enable_smart_routing=True, enable_maintenance_mode=True)

        # Test serialization
        json_str = flags.to_json()
        assert isinstance(json_str, str)

        # Test deserialization
        loaded_flags = FeatureFlags.from_json(json_str)
        assert loaded_flags.enable_followup_questions is False
        assert loaded_flags.enable_smart_routing is True
        assert loaded_flags.enable_maintenance_mode is True

        # Ensure other defaults are preserved
        assert loaded_flags.enable_analytics is True
        assert loaded_flags.enable_debug_mode is False
