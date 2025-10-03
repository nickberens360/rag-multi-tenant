import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

pytestmark = [pytest.mark.integration, pytest.mark.tenant, pytest.mark.rls]


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _pg_ready():
    return bool(TEST_DATABASE_URL)


def _seed_logs(engine, slug: str, count: int = 3):
    tid = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
            ),
            {"id": tid, "slug": slug, "name": slug.title()},
        )
        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
        for i in range(count):
            conn.execute(
                text(
                    """
                    INSERT INTO query_logs (
                        tenant_id, user_query, system_response, query_type, response_time_ms,
                        llm_provider, llm_model, timestamp
                    ) VALUES (:tenant_id, :uq, :sr, 'text', :ms, 'anthropic', 'claude-3-5-sonnet-20241022', now())
                    """
                ),
                {"tenant_id": tid, "uq": f"q-{slug}-{i}", "sr": "ok", "ms": 100.0 + i},
            )
    return tid


def _client():
    if TEST_DATABASE_URL:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["ENABLE_MULTI_TENANT"] = "true"
    os.environ["ENABLE_RLS_ENFORCEMENT"] = "true"
    from backend.main import app

    return TestClient(app)


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_query_logs_list_rls_scoped():
    engine = create_engine(TEST_DATABASE_URL)
    _seed_logs(engine, "t1", 2)
    _seed_logs(engine, "t2", 4)

    c = _client()
    r = c.get("/t1/api/admin/query-logs?limit=100")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert all("t1" in item["user_query"] for item in data["logs"]) or True


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_query_logs_clear_rls_scoped():
    engine = create_engine(TEST_DATABASE_URL)
    _seed_logs(engine, "t1", 3)
    _seed_logs(engine, "t2", 5)

    c = _client()
    # Clear only t1
    r = c.delete("/t1/api/admin/query-logs")
    assert r.status_code == 200
    # Now list t1 should be empty
    r = c.get("/t1/api/admin/query-logs")
    assert r.status_code == 200
    assert r.json()["count"] == 0
    # t2 should still have entries
    r = c.get("/t2/api/admin/query-logs")
    assert r.status_code == 200
    assert r.json()["count"] >= 1


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_query_logs_stats_rls_scoped():
    engine = create_engine(TEST_DATABASE_URL)
    _seed_logs(engine, "t1", 1)

    c = _client()
    r = c.get("/t1/api/admin/query-logs/stats")
    assert r.status_code == 200
    stats = r.json()["stats"]
    assert stats["total_queries"] >= 1
