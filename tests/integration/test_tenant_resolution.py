import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.integration, pytest.mark.tenant]


def _get_app():
    # Import here to respect test environment settings
    from backend.main import app

    return app


def test_path_prefix_resolution_returns_200():
    app = _get_app()
    client = TestClient(app)
    # Use debug endpoint under path-prefix to validate routing and context
    resp = client.get("/tenant1/api/debug/tenant")
    assert resp.status_code == 200


def test_subdomain_resolution_returns_200():
    app = _get_app()
    client = TestClient(app)
    # Subdomain precedence is handled by middleware; we just verify route works.
    resp = client.get("/api/health", headers={"Host": "tenant1.localhost"})
    assert resp.status_code == 200
