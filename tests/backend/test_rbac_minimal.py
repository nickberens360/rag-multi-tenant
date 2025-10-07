import pytest

from backend.core import rbac


class DummySession(dict):
    pass


def test_platform_admin_allows_any(monkeypatch):
    session = DummySession(user_id=1)

    def fake_effective(user_id, tenant_id):
        return {rbac.PLATFORM_ADMIN}

    monkeypatch.setattr(rbac, "get_effective_permissions", fake_effective)

    # No tenant_id provided but platform admin should allow
    rbac.authorize(session, rbac.DATA_WRITE, tenant_id=None)
    rbac.authorize(session, rbac.TENANT_MANAGE, tenant_id=None)
    rbac.authorize(session, rbac.PLATFORM_ADMIN, tenant_id=None)


def test_tenant_permission_requires_scope(monkeypatch):
    session = DummySession(user_id=2)

    def fake_effective(user_id, tenant_id):
        return {rbac.DATA_WRITE}

    monkeypatch.setattr(rbac, "get_effective_permissions", fake_effective)

    with pytest.raises(Exception):
        rbac.authorize(session, rbac.DATA_WRITE, tenant_id=None)


def test_insufficient_permissions_denied(monkeypatch):
    session = DummySession(user_id=3)

    def fake_effective(user_id, tenant_id):
        return {rbac.DATA_READ}

    monkeypatch.setattr(rbac, "get_effective_permissions", fake_effective)

    with pytest.raises(Exception):
        rbac.authorize(session, rbac.DATA_WRITE, tenant_id="00000000-0000-0000-0000-000000000001")


def test_member_allows_read_write(monkeypatch):
    session = DummySession(user_id=4)

    def fake_effective(user_id, tenant_id):
        return {rbac.DATA_READ, rbac.DATA_WRITE}

    monkeypatch.setattr(rbac, "get_effective_permissions", fake_effective)

    rbac.authorize(session, rbac.DATA_READ, tenant_id="00000000-0000-0000-0000-000000000001")
    rbac.authorize(session, rbac.DATA_WRITE, tenant_id="00000000-0000-0000-0000-000000000001")

