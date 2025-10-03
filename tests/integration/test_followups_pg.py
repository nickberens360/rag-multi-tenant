import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

pytestmark = [pytest.mark.integration, pytest.mark.tenant, pytest.mark.rls]


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _pg_ready():
    return bool(TEST_DATABASE_URL)


def _seed_tenant(engine, slug: str) -> str:
    tid = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
            ),
            {"id": tid, "slug": slug, "name": slug.title()},
        )
    return tid


def _client_with_admin():
    if TEST_DATABASE_URL:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["ENABLE_MULTI_TENANT"] = "true"
    os.environ["ENABLE_RLS_ENFORCEMENT"] = "true"
    from backend.core.admin_auth import require_admin_auth
    from backend.main import app

    app.dependency_overrides[require_admin_auth] = lambda: {"user_id": 1, "username": "tester"}
    return TestClient(app)


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_followup_category_crud_rls_scoped():
    engine = create_engine(TEST_DATABASE_URL)
    _seed_tenant(engine, "t1")
    _seed_tenant(engine, "t2")

    c = _client_with_admin()

    # Create category in t1
    resp = c.post(
        "/t1/api/admin/settings/followup/categories",
        json={"name": "testing", "display_name": "Testing", "description": "D", "icon": "test", "sort_order": 1},
    )
    assert resp.status_code == 200
    cat_id = resp.json()["id"]

    # List in t1 should include it
    resp = c.get("/t1/api/admin/settings/followup/categories")
    assert any(cat["id"] == cat_id for cat in resp.json())

    # List in t2 should not include it
    resp = c.get("/t2/api/admin/settings/followup/categories")
    assert all(cat.get("name") != "testing" for cat in resp.json())

    # Create question under category
    resp = c.post(
        "/t1/api/admin/settings/followup/questions",
        json={"category_id": cat_id, "question_text": "Q?", "sort_order": 1},
    )
    assert resp.status_code == 200
    q_id = resp.json()["id"]

    # Update question
    resp = c.put(f"/t1/api/admin/settings/followup/questions/{q_id}", json={"question_text": "Q2?"})
    assert resp.status_code == 200

    # Delete category by move strategy should error without target
    resp = c.post(f"/t1/api/admin/settings/followup/categories/{cat_id}/delete", json={"strategy": "move"})
    assert resp.status_code == 400

    # Deactivate category
    resp = c.post(f"/t1/api/admin/settings/followup/categories/{cat_id}/delete", json={"strategy": "deactivate"})
    assert resp.status_code == 200
