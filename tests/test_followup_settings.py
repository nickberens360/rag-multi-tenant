"""Tests for follow-up settings functionality."""

import json
from unittest.mock import patch

import pytest

from backend.core.followup_service import FollowUpService
from backend.core.settings_schemas import FollowUpSettings


class TestFollowUpSettings:
    """Test cases for FollowUpSettings configuration."""

    @pytest.mark.unit
    def test_followup_settings_defaults(self):
        """Test that FollowUpSettings initializes with correct defaults."""
        settings = FollowUpSettings()

        assert settings.enabled is True
        assert settings.service_type == "static"
        assert settings.max_questions == 1
        assert settings.relevance_threshold == 0.7
        assert settings.include_technical is True
        assert settings.include_personal is True
        assert settings.include_creative is True
        assert settings.question_style == "conversational"

    @pytest.mark.unit
    def test_followup_settings_to_dict(self):
        """Test FollowUpSettings to_dict conversion."""
        settings = FollowUpSettings(enabled=False, service_type="dynamic", max_questions=3, relevance_threshold=0.8)

        result = settings.to_dict()

        assert isinstance(result, dict)
        assert result["enabled"] is False
        assert result["service_type"] == "dynamic"
        assert result["max_questions"] == 3
        assert result["relevance_threshold"] == 0.8

    @pytest.mark.unit
    def test_followup_settings_from_dict(self):
        """Test FollowUpSettings from_dict creation with validation."""
        data = {
            "enabled": False,
            "service_type": "contextual",
            "max_questions": 5,
            "relevance_threshold": 0.9,
            "include_technical": False,
            "question_style": "formal",
        }

        settings = FollowUpSettings.from_dict(data)

        assert settings.enabled is False
        assert settings.service_type == "contextual"
        assert settings.max_questions == 5
        assert settings.relevance_threshold == 0.9
        assert settings.include_technical is False
        assert settings.question_style == "formal"
        # Should use defaults for missing keys
        assert settings.include_personal is True
        assert settings.include_creative is True

    @pytest.mark.unit
    def test_followup_settings_validation(self):
        """Test FollowUpSettings validation and bounds checking."""
        # Test max_questions bounds
        settings1 = FollowUpSettings.from_dict({"max_questions": 10})
        assert settings1.max_questions == 5  # Should be capped at 5

        settings2 = FollowUpSettings.from_dict({"max_questions": 0})
        assert settings2.max_questions == 1  # Should be minimum 1

        # Test relevance_threshold bounds
        settings3 = FollowUpSettings.from_dict({"relevance_threshold": 1.5})
        assert settings3.relevance_threshold == 1.0  # Should be capped at 1.0

        settings4 = FollowUpSettings.from_dict({"relevance_threshold": -0.1})
        assert settings4.relevance_threshold == 0.1  # Should be minimum 0.1

        # Test invalid service_type
        settings5 = FollowUpSettings.from_dict({"service_type": "invalid"})
        assert settings5.service_type == "static"  # Should default to static

        # Test invalid question_style
        settings6 = FollowUpSettings.from_dict({"question_style": "invalid"})
        assert settings6.question_style == "conversational"  # Should default to conversational

    @pytest.mark.unit
    def test_followup_settings_json_serialization(self):
        """Test JSON serialization and deserialization."""
        original = FollowUpSettings(enabled=True, service_type="dynamic", max_questions=3, relevance_threshold=0.6)

        # Test to_json
        json_str = original.to_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["enabled"] is True
        assert data["service_type"] == "dynamic"

        # Test from_json
        restored = FollowUpSettings.from_json(json_str)
        assert restored.enabled == original.enabled
        assert restored.service_type == original.service_type
        assert restored.max_questions == original.max_questions
        assert restored.relevance_threshold == original.relevance_threshold

    @pytest.mark.unit
    def test_followup_settings_json_error_handling(self):
        """Test JSON parsing error handling."""
        # Invalid JSON should return defaults
        incomplete_json = "{"  # Incomplete JSON with unclosed brace
        settings = FollowUpSettings.from_json(incomplete_json)

        # Should be default settings
        default_settings = FollowUpSettings()
        assert settings.enabled == default_settings.enabled
        assert settings.service_type == default_settings.service_type


class TestFollowUpServiceConfigurable:
    """Test cases for configurable FollowUpService."""

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_disabled_settings(self, mock_db_manager):
        """Test that disabled settings return no questions."""
        settings = FollowUpSettings(enabled=False)
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()
        result = service.generate_followups("test question", "test response")

        assert result == []

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_max_questions_setting(self, mock_db_manager):
        """Test that max_questions setting is respected."""
        settings = FollowUpSettings(enabled=True, max_questions=3)
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()
        result = service.generate_followups("test question", "test response")

        assert len(result) == 3
        assert all(isinstance(q, str) for q in result)

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_category_filtering(self, mock_db_manager):
        """Test that category filtering works correctly."""
        # Only enable technical questions
        settings = FollowUpSettings(
            enabled=True, include_technical=True, include_personal=False, include_creative=False, max_questions=5
        )
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        # Mock database to provide fallback categories but no database questions
        # This will trigger fallback to hardcoded question pools
        mock_db_manager.get_followup_categories.return_value = [
            {"id": 1, "name": "technical", "display_name": "Technical", "is_active": True},
            {"id": 2, "name": "personal", "display_name": "Personal", "is_active": True},
            {"id": 3, "name": "creative", "display_name": "Creative", "is_active": True},
        ]
        mock_db_manager.get_followup_questions.return_value = []  # No database questions

        service = FollowUpService()
        result = service.generate_followups("test question", "test response")

        # All returned questions should be from technical category since other categories are disabled
        for question in result:
            assert question in service.question_pools["technical"]

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_service_type_static(self, mock_db_manager):
        """Test static service type behavior."""
        settings = FollowUpSettings(enabled=True, service_type="static", max_questions=2)
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()

        # Call multiple times to test sequential behavior
        result1 = service.generate_followups("question1", "response1")
        result2 = service.generate_followups("question2", "response2")

        assert len(result1) == 2
        assert len(result2) == 2
        # Questions should be different between calls (sequential)
        assert result1 != result2

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_service_type_dynamic(self, mock_db_manager):
        """Test dynamic service type behavior."""
        settings = FollowUpSettings(enabled=True, service_type="dynamic", max_questions=2)
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()
        result = service.generate_followups("test question", "test response")

        assert len(result) == 2
        assert all(isinstance(q, str) for q in result)

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_settings_caching(self, mock_db_manager):
        """Test that settings are cached to reduce database calls."""
        settings = FollowUpSettings(enabled=True)
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()

        # First call should hit database
        service.generate_followups("test1", "response1")
        assert mock_db_manager.get_admin_setting.call_count == 1

        # Second call within cache period should not hit database
        service.generate_followups("test2", "response2")
        assert mock_db_manager.get_admin_setting.call_count == 1  # Same count

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_settings_reload(self, mock_db_manager):
        """Test that settings can be reloaded manually."""
        settings = FollowUpSettings(enabled=True)
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()

        # Load settings initially
        service.generate_followups("test", "response")
        initial_call_count = mock_db_manager.get_admin_setting.call_count

        # Reload settings manually
        service.reload_settings()

        # Next call should reload from database
        service.generate_followups("test", "response")
        assert mock_db_manager.get_admin_setting.call_count > initial_call_count

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_database_error_fallback(self, mock_db_manager):
        """Test fallback behavior when database is unavailable."""
        # Mock database to raise an exception
        mock_db_manager.get_admin_setting.side_effect = Exception("Database error")

        service = FollowUpService()

        # Should not raise exception and return fallback behavior
        result = service.generate_followups("test", "response")

        # Should return a result from fallback (default questions)
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0] in service.default_questions

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_no_categories_enabled(self, mock_db_manager):
        """Test behavior when no question categories are enabled."""
        settings = FollowUpSettings(
            enabled=True, include_technical=False, include_personal=False, include_creative=False
        )
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()
        result = service.generate_followups("test", "response")

        # Should fall back to default questions when no categories enabled
        assert len(result) >= 1
        assert result[0] in service.default_questions

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_thread_safety_with_settings(self, mock_db_manager):
        """Test thread safety when loading settings concurrently."""
        settings = FollowUpSettings(enabled=True, max_questions=1)
        mock_db_manager.get_admin_setting.return_value = settings.to_json()

        service = FollowUpService()
        results = []

        def worker():
            result = service.generate_followups("test", "response")
            results.append(result)

        # Start multiple threads
        import threading

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should have results from all threads
        assert len(results) == 10
        # All should be valid results
        for result in results:
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], str)

    @pytest.mark.unit
    @patch("backend.core.followup_service.admin_db_manager")
    def test_invalid_json_in_database(self, mock_db_manager):
        """Test handling of invalid JSON stored in database."""
        # Mock database to return invalid JSON
        mock_db_manager.get_admin_setting.return_value = "invalid json {"

        service = FollowUpService()

        # Should not raise exception and use default settings
        result = service.generate_followups("test", "response")

        assert isinstance(result, list)
        assert len(result) >= 1  # Should use default max_questions=1
