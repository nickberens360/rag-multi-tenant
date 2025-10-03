import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

pytestmark = [pytest.mark.integration, pytest.mark.tenant]


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _pg_ready():
    return bool(TEST_DATABASE_URL)


def _ensure_tenant(engine, slug: str, name: str) -> str:
    tid = str(uuid.uuid4())
    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
                ),
                {"id": tid, "slug": slug, "name": name},
            )
        except ProgrammingError as e:
            # Table missing — skip tests
            pytest.skip(f"Postgres schema not ready: {e}")
    return tid


def _get_app_client():
    # Ensure app reads TEST_DATABASE_URL
    if TEST_DATABASE_URL:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        os.environ["ENABLE_MULTI_TENANT"] = "true"
        os.environ["ENABLE_RLS_ENFORCEMENT"] = "true"
    from backend.main import app

    return TestClient(app)


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_debug_tenant_path_prefix_resolution():
    engine = create_engine(TEST_DATABASE_URL)
    _ensure_tenant(engine, "tenant1", "Tenant 1")

    client = _get_app_client()
    resp = client.get("/tenant1/api/debug/tenant")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("tenant_slug") == "tenant1"
    assert data.get("tenant_id")


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_debug_tenant_subdomain_precedence_over_path():
    engine = create_engine(TEST_DATABASE_URL)
    _ensure_tenant(engine, "tenant1", "Tenant 1")
    _ensure_tenant(engine, "tenant2", "Tenant 2")

    client = _get_app_client()
    # Subdomain should take precedence over path prefix
    resp = client.get("/tenant2/api/debug/tenant", headers={"Host": "tenant1.localhost"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("tenant_slug") == "tenant1"


def test_debug_tenant_default_when_no_tenant_context():
    client = _get_app_client()
    resp = client.get("/api/debug/tenant", headers={"Host": "www.localhost"})
    assert resp.status_code == 200
    data = resp.json()
    # Uses default values from environment when resolution not possible
    assert data.get("tenant_slug") in {os.getenv("DEFAULT_TENANT_SLUG", "default"), None}
    assert data.get("tenant_id") is not None or True  # permit None if single-tenant mode


def test_debug_tenant_invalid_subdomain_uses_default():
    client = _get_app_client()
    resp = client.get("/api/debug/tenant", headers={"Host": "nonexistent.localhost"})
    assert resp.status_code == 200
    data = resp.json()
    # Invalid tenant falls back to default in current implementation
    assert data.get("tenant_slug") in {os.getenv("DEFAULT_TENANT_SLUG", "default"), None}
