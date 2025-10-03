"""Tests for admin settings API endpoints."""

from unittest.mock import Mock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.core.settings_schemas import FollowUpSettings


class TestAdminSettingsAPI:
    """Test cases for admin settings API endpoints."""

    @pytest.fixture
    def mock_session(self):
        """Mock admin session for authentication."""
        return {"user_id": 1, "username": "testadmin", "role": "admin"}

    @pytest.fixture
    def client(self):
        """Create test client."""
        from backend.main import app

        return TestClient(app)

    @pytest.mark.unit
    @patch("backend.routes.admin.get_settings_manager")
    def test_get_followup_settings_no_existing_settings(self, mock_get_settings_manager, client, mock_session):
        """Test GET /settings/followup when no settings exist."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session

        # Mock the settings manager to return default settings
        default_settings = FollowUpSettings()
        mock_settings_manager = Mock()
        mock_settings_manager.get_followup_settings.return_value = default_settings
        mock_get_settings_manager.return_value = mock_settings_manager

        try:
            response = client.get("/api/admin/settings/followup")
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return default settings
        assert data["enabled"] == default_settings.enabled
        assert data["service_type"] == default_settings.service_type
        assert data["max_questions"] == default_settings.max_questions

    @pytest.mark.unit
    @patch("backend.routes.admin.get_settings_manager")
    def test_get_followup_settings_existing_settings(self, mock_get_settings_manager, client, mock_session):
        """Test GET /settings/followup when settings exist."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session

        # Mock the settings manager to return specific settings
        existing_settings = FollowUpSettings(enabled=False, service_type="dynamic", max_questions=3)
        mock_settings_manager = Mock()
        mock_settings_manager.get_followup_settings.return_value = existing_settings
        mock_get_settings_manager.return_value = mock_settings_manager

        try:
            response = client.get("/api/admin/settings/followup")
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["enabled"] is False
        assert data["service_type"] == "dynamic"
        assert data["max_questions"] == 3

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    def test_update_followup_settings_success(self, mock_db_manager, client, mock_session):
        """Test PUT /settings/followup with valid data."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session
        mock_db_manager.set_admin_setting.return_value = True

        settings_data = {
            "enabled": True,
            "service_type": "contextual",
            "max_questions": 2,
            "relevance_threshold": 0.8,
            "include_technical": True,
            "include_personal": False,
            "include_creative": True,
            "question_style": "formal",
        }

        try:
            response = client.put("/api/admin/settings/followup", json=settings_data)
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "message" in data
        assert data["settings"]["enabled"] is True
        assert data["settings"]["service_type"] == "contextual"
        assert data["settings"]["max_questions"] == 2

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    def test_update_followup_settings_validation(self, mock_db_manager, client, mock_session):
        """Test that settings validation works during update."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session
        mock_db_manager.set_admin_setting.return_value = True

        # Send invalid values that should be corrected
        settings_data = {
            "enabled": "true",  # String instead of bool
            "service_type": "invalid_type",  # Invalid service type
            "max_questions": 10,  # Too high, should be capped at 5
            "relevance_threshold": 2.0,  # Too high, should be capped at 1.0
            "question_style": "invalid_style",  # Invalid style
        }

        try:
            response = client.put("/api/admin/settings/followup", json=settings_data)
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check that validation corrected the values
        assert data["settings"]["enabled"] is True  # String "true" converted to bool
        assert data["settings"]["service_type"] == "static"  # Invalid type defaulted
        assert data["settings"]["max_questions"] == 5  # Capped at maximum
        assert data["settings"]["relevance_threshold"] == 1.0  # Capped at maximum
        assert data["settings"]["question_style"] == "conversational"  # Invalid style defaulted

    @pytest.mark.unit
    @patch("backend.routes.admin.get_settings_manager")
    def test_update_followup_settings_database_error(self, mock_get_settings_manager, client, mock_session):
        """Test PUT /settings/followup when database save fails."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session

        # Mock the settings manager to return failure on set
        mock_settings_manager = Mock()
        mock_settings_manager.set_followup_settings.return_value = False
        mock_get_settings_manager.return_value = mock_settings_manager

        settings_data = {"enabled": False, "service_type": "static"}

        try:
            response = client.put("/api/admin/settings/followup", json=settings_data)
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Error updating follow-up settings" in data["detail"]

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    def test_reset_followup_settings_success(self, mock_db_manager, client, mock_session):
        """Test POST /settings/followup/reset."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session
        mock_db_manager.set_admin_setting.return_value = True

        try:
            response = client.post("/api/admin/settings/followup/reset")
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "reset to defaults" in data["message"]

        # Should return default settings
        default_settings = FollowUpSettings()
        assert data["settings"]["enabled"] == default_settings.enabled
        assert data["settings"]["service_type"] == default_settings.service_type
        assert data["settings"]["max_questions"] == default_settings.max_questions

    @pytest.mark.unit
    @patch("backend.routes.admin.get_settings_manager")
    def test_reset_followup_settings_database_error(self, mock_get_settings_manager, client, mock_session):
        """Test POST /settings/followup/reset when database save fails."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session

        # Mock the settings manager to return failure on set
        mock_settings_manager = Mock()
        mock_settings_manager.set_followup_settings.return_value = False
        mock_get_settings_manager.return_value = mock_settings_manager

        try:
            response = client.post("/api/admin/settings/followup/reset")
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Error resetting follow-up settings" in data["detail"]

    @pytest.mark.unit
    @patch("backend.routes.admin.require_admin_auth")
    def test_settings_authentication_required(self, mock_auth, client):
        """Test that all settings endpoints require authentication."""
        from fastapi import HTTPException

        mock_auth.side_effect = HTTPException(status_code=401, detail="Authentication required")

        # Test GET endpoint
        response = client.get("/api/admin/settings/followup")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test PUT endpoint
        response = client.put("/api/admin/settings/followup", json={})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Test POST endpoint
        response = client.post("/api/admin/settings/followup/reset")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.unit
    @patch("backend.routes.admin.get_settings_manager")
    @patch("backend.routes.admin.audit_logger")
    def test_settings_audit_logging(self, mock_audit, mock_get_settings_manager, client, mock_session):
        """Test that settings changes are properly audited."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session

        # Mock the settings manager
        mock_settings_manager = Mock()
        default_settings = FollowUpSettings()
        mock_settings_manager.get_followup_settings.return_value = default_settings
        mock_settings_manager.set_followup_settings.return_value = True
        mock_get_settings_manager.return_value = mock_settings_manager

        try:
            # Test GET request audit
            response = client.get("/api/admin/settings/followup")
            assert response.status_code == status.HTTP_200_OK
            # Check that audit logging was called (using the actual signature)
            mock_audit.log_action.assert_called()

            # Get the first call args and verify the audit log call
            first_call = mock_audit.log_action.call_args_list[0]
            call_kwargs = first_call[1]  # Get keyword arguments
            assert call_kwargs["username"] == mock_session["username"]
            assert call_kwargs["details"]["resource"] == "followup_settings"

            # Test PUT request audit
            settings_data = {"enabled": False}
            response = client.put("/api/admin/settings/followup", json=settings_data)
            assert response.status_code == status.HTTP_200_OK

            # Should log the update action - verify at least 2 calls were made
            assert len(mock_audit.log_action.call_args_list) >= 2
            # Verify the second call has appropriate details
            second_call = mock_audit.log_action.call_args_list[1]
            second_kwargs = second_call[1]
            assert second_kwargs["username"] == mock_session["username"]
            assert "details" in second_kwargs
        finally:
            # Clean up
            app.dependency_overrides.clear()

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    def test_malformed_json_handling(self, mock_db_manager, client, mock_session):
        """Test handling of malformed JSON in request."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session

        try:
            # Send malformed JSON
            response = client.put(
                "/api/admin/settings/followup", data="invalid json {", headers={"content-type": "application/json"}
            )
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    def test_empty_request_body(self, mock_db_manager, client, mock_session):
        """Test handling of empty request body."""
        from backend.core.admin_auth import require_admin_auth
        from backend.main import app

        # Override the dependency
        app.dependency_overrides[require_admin_auth] = lambda: mock_session
        mock_db_manager.set_admin_setting.return_value = True

        try:
            # Send empty JSON object
            response = client.put("/api/admin/settings/followup", json={})
        finally:
            # Clean up
            app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should use default settings
        assert data["success"] is True
        default_settings = FollowUpSettings()
        assert data["settings"]["enabled"] == default_settings.enabled
