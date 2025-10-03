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
def test_welcome_questions_crud_rls_scoped():
    engine = create_engine(TEST_DATABASE_URL)
    _seed_tenant(engine, "t1")
    _seed_tenant(engine, "t2")

    c = _client_with_admin()

    # Create in t1
    resp = c.post("/t1/api/admin/settings/welcome/questions", json={"question_text": "Hello?", "sort_order": 1})
    assert resp.status_code == 200
    qid = resp.json()["id"]

    # List in t1 includes it
    resp = c.get("/t1/api/admin/settings/welcome/questions")
    assert any(q["id"] == qid for q in resp.json())

    # List in t2 should not include it
    resp = c.get("/t2/api/admin/settings/welcome/questions")
    assert all(q["id"] != qid for q in resp.json())

    # Update
    resp = c.put(f"/t1/api/admin/settings/welcome/questions/{qid}", json={"question_text": "Hi?"})
    assert resp.status_code == 200

    # Delete
    resp = c.delete(f"/t1/api/admin/settings/welcome/questions/{qid}")
    assert resp.status_code == 200
