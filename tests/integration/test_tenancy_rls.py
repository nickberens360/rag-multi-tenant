import os
import uuid

import pytest
from sqlalchemy import create_engine, text

pytestmark = [pytest.mark.integration, pytest.mark.rls, pytest.mark.tenant]


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def require_test_db():
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set; skipping RLS tests")


def _setup_engine():
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    return engine


def test_rls_isolation_admin_settings():
    require_test_db()
    engine = _setup_engine()

    t1 = str(uuid.uuid4())
    t2 = str(uuid.uuid4())

    with engine.begin() as conn:
        # Ensure base schema exists (expects alembic run beforehand)
        # Create tenants
        conn.execute(
            text(
                "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
            ),
            {"id": t1, "slug": "tenant1", "name": "Tenant 1"},
        )
        conn.execute(
            text(
                "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
            ),
            {"id": t2, "slug": "tenant2", "name": "Tenant 2"},
        )

        # Insert admin_settings for tenant1
        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": t1})
        conn.execute(
            text(
                "INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at) VALUES (:tid, :k, :v, now())"
            ),
            {"tid": t1, "k": "k1", "v": "v1"},
        )

        # Insert admin_settings for tenant2
        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": t2})
        conn.execute(
            text(
                "INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at) VALUES (:tid, :k, :v, now())"
            ),
            {"tid": t2, "k": "k1", "v": "v2"},
        )

        # Query as tenant1
        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": t1})
        rows = conn.execute(text("SELECT setting_value FROM admin_settings WHERE setting_key = 'k1'"))
        assert [r[0] for r in rows.fetchall()] == ["v1"]

        # Query as tenant2
        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": t2})
        rows = conn.execute(text("SELECT setting_value FROM admin_settings WHERE setting_key = 'k1'"))
        assert [r[0] for r in rows.fetchall()] == ["v2"]


def test_rls_insert_wrong_tenant_blocked():
    require_test_db()
    engine = _setup_engine()

    t1 = str(uuid.uuid4())
    t2 = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
            ),
            {"id": t1, "slug": "t1", "name": "T1"},
        )
        conn.execute(
            text(
                "INSERT INTO tenants (id, slug, name, created_at, updated_at) VALUES (:id, :slug, :name, now(), now())"
            ),
            {"id": t2, "slug": "t2", "name": "T2"},
        )

        conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": t1})
        with pytest.raises(Exception):
            conn.execute(
                text(
                    "INSERT INTO admin_settings (tenant_id, setting_key, setting_value, updated_at) VALUES (:tid, 'k2', 'bad', now())"
                ),
                {"tid": t2},
            )
