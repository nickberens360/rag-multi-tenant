"""Minimal RBAC authorization helpers.

Implements a small permission catalog evaluation with tenant scoping.
Use `authorize(session, permission, tenant_id)` in FastAPI dependencies.
"""

from __future__ import annotations

from typing import Optional, Set

from fastapi import HTTPException, status
from sqlalchemy import text

from .db_session import get_db_session_sync


# Permission slugs (canonical)
PLATFORM_ADMIN = "platform:admin"
TENANT_MANAGE = "tenant:manage"
USER_MANAGE = "user:manage"
DATA_READ = "data:read"
DATA_WRITE = "data:write"


def get_effective_permissions(user_id: int, tenant_id: Optional[str]) -> Set[str]:
    """Compute effective permission slugs for a user within an optional tenant scope.

    Includes platform-scope role permissions (tenant_id NULL) and, if provided,
    tenant-scoped role permissions for the specified tenant.
    """
    if user_id <= 0:
        return set()

    perms: Set[str] = set()

    try:
        with get_db_session_sync() as session:
            if session is None:
                return perms

            # Collect platform role permissions (tenant_id IS NULL)
            rows = session.execute(
                text(
                    """
                    SELECT DISTINCT p.slug
                    FROM user_roles ur
                    JOIN roles r ON r.id = ur.role_id
                    JOIN role_permissions rp ON rp.role_id = r.id
                    JOIN permissions p ON p.id = rp.permission_id
                    WHERE ur.user_id = :uid AND ur.tenant_id IS NULL
                    """
                ),
                {"uid": user_id},
            ).fetchall()
            perms.update(r[0] for r in rows)

            # Collect tenant role permissions when scoped
            if tenant_id:
                rows = session.execute(
                    text(
                        """
                        SELECT DISTINCT p.slug
                        FROM user_roles ur
                        JOIN roles r ON r.id = ur.role_id
                        JOIN role_permissions rp ON rp.role_id = r.id
                        JOIN permissions p ON p.id = rp.permission_id
                        WHERE ur.user_id = :uid AND ur.tenant_id = :tid
                        """
                    ),
                    {"uid": user_id, "tid": tenant_id},
                ).fetchall()
                perms.update(r[0] for r in rows)

    except Exception:
        # Fail-closed by returning empty set; caller will deny
        return perms

    return perms


def authorize(session: dict, permission: str, tenant_id: Optional[str]) -> None:
    """Authorize a request for a given permission within an optional tenant scope.

    Rules:
    - If user has PLATFORM_ADMIN permission at platform scope, allow all.
    - For tenant-scoped permissions, a tenant_id must be provided.
    - Default deny if permission is absent.
    """
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user_id = int(session.get("user_id", 0))
    effective = get_effective_permissions(user_id, tenant_id)

    # Short-circuit for platform admin
    if PLATFORM_ADMIN in effective:
        return

    # Platform permission requires explicit membership
    if permission == PLATFORM_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin required")

    # Tenant permissions require tenant scope
    if permission in {TENANT_MANAGE, USER_MANAGE, DATA_READ, DATA_WRITE} and not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant scope required")

    if permission not in effective:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Authorized
    return None

