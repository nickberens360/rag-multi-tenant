"""
Tests for dependencies module.

This module contains tests for FastAPI dependency functions that provide
access to application state and services through dependency injection.
"""

from unittest.mock import MagicMock

import pytest

from backend.dependencies import get_app_state, get_services


class TestDependencies:
    """Test cases for dependency functions."""

    @pytest.mark.unit
    def test_get_app_state_with_initialized_app(self):
        """Test get_app_state returns correct state when app is initialized."""
        # Create mock request with app state
        mock_request = MagicMock()
        mock_request.app.state.app_initialized = True
        mock_request.app.state.illustration_service = MagicMock()

        result = get_app_state(mock_request)

        assert result["app_initialized"] is True
        assert result["illustration_service"] is not None

    @pytest.mark.unit
    def test_get_app_state_with_uninitialized_app(self):
        """Test get_app_state returns correct state when app is not initialized."""
        # Create mock request with uninitialized app state
        mock_request = MagicMock()
        mock_request.app.state.app_initialized = False
        mock_request.app.state.illustration_service = None

        result = get_app_state(mock_request)

        assert result["app_initialized"] is False
        assert result["illustration_service"] is None

    @pytest.mark.unit
    def test_get_app_state_with_missing_attributes(self):
        """Test get_app_state handles missing attributes gracefully."""
        # Create mock request without some attributes
        mock_request = MagicMock()
        # Remove attributes to simulate missing state
        del mock_request.app.state.app_initialized
        del mock_request.app.state.illustration_service

        result = get_app_state(mock_request)

        # Should return default values when attributes are missing
        assert result["app_initialized"] is False
        assert result["illustration_service"] is None

    @pytest.mark.unit
    def test_get_services_with_all_services_available(self):
        """Test get_services returns all services when available."""
        # Create mock request with all services
        mock_request = MagicMock()
        mock_request.app.state.retrievers = {"resume": MagicMock()}
        mock_request.app.state.illustration_service = MagicMock()
        mock_request.app.state.query_router = MagicMock()
        mock_request.app.state.response_service = MagicMock()
        mock_request.app.state.followup_service = MagicMock()

        result = get_services(mock_request)

        assert result["retrievers"] is not None
        assert result["illustration_service"] is not None
        assert result["query_router"] is not None
        assert result["response_service"] is not None
        assert result["followup_service"] is not None

    @pytest.mark.unit
    def test_get_services_with_missing_services(self):
        """Test get_services handles missing services gracefully."""
        # Create mock request with some missing services
        mock_request = MagicMock()
        mock_request.app.state.retrievers = None
        mock_request.app.state.illustration_service = MagicMock()
        # Remove some attributes to simulate missing services
        del mock_request.app.state.query_router
        del mock_request.app.state.response_service
        del mock_request.app.state.followup_service

        result = get_services(mock_request)

        assert result["retrievers"] is None
        assert result["illustration_service"] is not None
        assert result["query_router"] is None
        assert result["response_service"] is None
        assert result["followup_service"] is None

    @pytest.mark.unit
    def test_get_services_with_no_app_state(self):
        """Test get_services handles completely missing app state."""
        # Create mock request without app state
        mock_request = MagicMock()
        # Remove all state attributes
        del mock_request.app.state.retrievers
        del mock_request.app.state.illustration_service
        del mock_request.app.state.query_router
        del mock_request.app.state.response_service
        del mock_request.app.state.followup_service

        result = get_services(mock_request)

        # Should return None for all services when not available
        assert result["retrievers"] is None
        assert result["illustration_service"] is None
        assert result["query_router"] is None
        assert result["response_service"] is None
        assert result["followup_service"] is None

    @pytest.mark.unit
    def test_get_app_state_return_structure(self):
        """Test that get_app_state returns the expected dictionary structure."""
        mock_request = MagicMock()
        mock_request.app.state.app_initialized = True
        mock_request.app.state.illustration_service = MagicMock()

        result = get_app_state(mock_request)

        # Verify the exact keys are present
        expected_keys = {"app_initialized", "illustration_service"}
        assert set(result.keys()) == expected_keys
        assert isinstance(result, dict)

    @pytest.mark.unit
    def test_get_services_return_structure(self):
        """Test that get_services returns the expected dictionary structure."""
        mock_request = MagicMock()
        mock_request.app.state.retrievers = MagicMock()
        mock_request.app.state.illustration_service = MagicMock()
        mock_request.app.state.query_router = MagicMock()
        mock_request.app.state.response_service = MagicMock()
        mock_request.app.state.followup_service = MagicMock()

        result = get_services(mock_request)

        # Verify the exact keys are present
        expected_keys = {"retrievers", "illustration_service", "query_router", "response_service", "followup_service"}
        assert set(result.keys()) == expected_keys
        assert isinstance(result, dict)

    @pytest.mark.unit
    def test_dependencies_are_independent(self):
        """Test that dependency functions don't interfere with each other."""
        mock_request = MagicMock()
        mock_request.app.state.app_initialized = True
        mock_request.app.state.illustration_service = MagicMock()
        mock_request.app.state.retrievers = MagicMock()
        mock_request.app.state.query_router = MagicMock()
        mock_request.app.state.response_service = MagicMock()
        mock_request.app.state.followup_service = MagicMock()

        # Call both functions
        app_state = get_app_state(mock_request)
        services = get_services(mock_request)

        # Verify they return different structures
        assert set(app_state.keys()) != set(services.keys())

        # Verify they both access the same illustration_service
        assert app_state["illustration_service"] is services["illustration_service"]

    @pytest.mark.unit
    def test_get_app_state_with_partial_state(self):
        """Test get_app_state with only some state attributes present."""
        mock_request = MagicMock()
        mock_request.app.state.app_initialized = True
        # illustration_service is missing
        del mock_request.app.state.illustration_service

        result = get_app_state(mock_request)

        assert result["app_initialized"] is True
        assert result["illustration_service"] is None
