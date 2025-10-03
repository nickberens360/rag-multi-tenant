import os
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

pytestmark = [pytest.mark.integration, pytest.mark.tenant]


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def _pg_ready():
    return bool(TEST_DATABASE_URL)


def _seed_tenant_and_logs(engine, slug: str = "tenant1") -> str:
    tid = str(uuid.uuid4())
    now = datetime.utcnow()
    with engine.begin() as conn:
        # Create tenant
        conn.execute(
            text(
                "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
            ),
            {"id": tid, "slug": slug, "name": slug.title()},
        )

        # Set tenant context for RLS
        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})

        # Insert a few query logs within the last 24h
        for ms, err in [(120.0, False), (200.0, False), (350.0, True)]:
            conn.execute(
                text(
                    """
                    INSERT INTO query_logs (
                        tenant_id, user_query, system_response, query_type, response_time_ms, error_occurred, timestamp
                    ) VALUES (:tenant_id, :uq, :sr, 'text', :ms, :err, :ts)
                    """
                ),
                {
                    "tenant_id": tid,
                    "uq": "test",
                    "sr": "ok",
                    "ms": ms,
                    "err": err,
                    "ts": now - timedelta(minutes=5),
                },
            )
    return tid


def _get_client():
    if TEST_DATABASE_URL:
        os.environ["DATABASE_URL"] = TEST_DATABASE_URL
        os.environ["ENABLE_MULTI_TENANT"] = "true"
        os.environ["ENABLE_RLS_ENFORCEMENT"] = "true"
    from backend.main import app

    return TestClient(app)


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_performance_timeline_uses_rls_postgres():
    engine = create_engine(TEST_DATABASE_URL)
    _seed_tenant_and_logs(engine, "tenant1")

    client = _get_client()
    resp = client.get("/tenant1/api/admin/performance/timeline?days=1&interval=hour")
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
    # Expect at least one bucket
    assert isinstance(data["timeline"], list)


@pytest.mark.skipif(not _pg_ready(), reason="TEST_DATABASE_URL not set")
def test_performance_percentiles_uses_rls_postgres():
    engine = create_engine(TEST_DATABASE_URL)
    _seed_tenant_and_logs(engine, "tenant1")

    client = _get_client()
    resp = client.get("/tenant1/api/admin/performance/percentiles?time_range=24h")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"p50", "p95", "p99"}
