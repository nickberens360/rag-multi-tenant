from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_query_api_smalltime():
    # Mock the heavy initialization to avoid timeout
    with (
        patch("backend.core.app_initializer_v2.initialize_app_state") as mock_init,
        patch("backend.core.llm_chain.get_rate_limit_status") as mock_rate_limit,
        patch("backend.security.validator.SecurityValidator.validate_query") as mock_validate,
        patch("backend.security.validator.SecurityValidator.sanitize_input") as mock_sanitize,
    ):

        # Mock rate limit status
        mock_rate_limit.return_value = {}

        # Mock security validation
        mock_validate.return_value = (True, None)
        mock_sanitize.side_effect = lambda x: x  # Return input unchanged

        # Make initialize_app_state return mock objects instead of doing heavy initialization
        mock_init.return_value = ({}, None, None)  # retrievers, illustration_service, llm

        from backend.dependencies import get_services
        from backend.main import app

        # Mock illustration service to return a result for 'smalltime'
        mock_illustration_service = MagicMock()
        mock_illustration_service.search.return_value = ["smalltime_artwork.jpg"]

        # Mock other required services
        mock_query_router = MagicMock()
        from backend.core.query_router import QueryType

        mock_query_router.route_query.return_value = (QueryType.SPECIFIC_IMAGE_SEARCH, "smalltime")

        mock_response_service = MagicMock()
        mock_response_data = MagicMock()
        mock_response_data.model_dump.return_value = {
            "response": "Here are illustrations for 'smalltime'.",
            "images": ["smalltime_artwork.jpg"],
            "followup_questions": [],
        }
        mock_response_service.build_image_response.return_value = mock_response_data

        mock_followup_service = MagicMock()
        mock_followup_service.generate_followups.return_value = []

        def mock_get_services():
            return {
                "illustration_service": mock_illustration_service,
                "query_router": mock_query_router,
                "response_service": mock_response_service,
                "followup_service": mock_followup_service,
                "retrievers": None,
            }

        # Override the dependency
        app.dependency_overrides[get_services] = mock_get_services

        try:
            client = TestClient(app)
            payload: Dict[str, Any] = {
                "question": "Tell me about the 'Smalltime' illustration",
                "chat_history": [],
                "preferred_model": None,
            }
            resp = client.post("/query", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            # Ensure images list is present and contains the Smalltime illustration
            assert "images" in data and isinstance(data["images"], list)
            assert any("smalltime" in img.lower() for img in data["images"]), data
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()
