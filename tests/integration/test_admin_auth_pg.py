import os
import uuid

import pytest

from backend.core.admin_auth import admin_auth_manager
from backend.core.db_session import get_db_session_sync

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="Postgres integration tests require TEST_DATABASE_URL",
)


@pytest.fixture(autouse=True)
def _patch_database_url(monkeypatch):
    test_db = os.getenv("TEST_DATABASE_URL")
    if test_db:
        monkeypatch.setenv("DATABASE_URL", test_db)


def test_rate_limiting_pg_basic():
    ip = "127.0.0.1"

    # Ensure clean state
    admin_auth_manager.reset_rate_limit(ip, "ip")

    # Determine threshold
    max_attempts = admin_auth_manager.get_dynamic_max_login_attempts()

    # Up to threshold - 1 should not lock
    for _ in range(max_attempts - 1):
        assert admin_auth_manager.record_rate_limit_attempt(ip, "ip", lockout_duration_minutes=1) is False

    # Threshold attempt should lock
    assert admin_auth_manager.record_rate_limit_attempt(ip, "ip", lockout_duration_minutes=1) is True
    assert admin_auth_manager.is_rate_limited(ip, "ip") is True

    # Reset should clear lockout
    assert admin_auth_manager.reset_rate_limit(ip, "ip") is True
    assert admin_auth_manager.is_rate_limited(ip, "ip") is False


def test_create_user_and_authenticate_pg():
    username = f"test_{uuid.uuid4().hex[:8]}"
    password = "Str0ngPass!A"

    # Create
    user_id = admin_auth_manager.create_admin_user(username=username, password=password, email=None, role="viewer")
    assert user_id > 0

    try:
        # Wrong password triggers failure
        assert (
            admin_auth_manager.authenticate_user(username, "wrong", ip_address="127.0.0.1", user_agent="pytest") is None
        )

        # Correct password succeeds
        result = admin_auth_manager.authenticate_user(username, password, ip_address="127.0.0.1", user_agent="pytest")
        assert result and "session_id" in result

    finally:
        # Cleanup user
        with get_db_session_sync() as session:
            session.execute("DELETE FROM admin_sessions WHERE user_id = :uid", {"uid": user_id})
            session.execute("DELETE FROM admin_users WHERE id = :uid", {"uid": user_id})
