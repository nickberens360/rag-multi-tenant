import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.admin_auth import require_admin_auth
from backend.core.db_session import get_db_session

router = APIRouter(prefix="/api/admin/tenants", tags=["tenants"])


@router.post("/")
async def create_tenant(
    data: Dict[str, Any], session: Session = Depends(get_db_session), admin=Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Create new tenant."""
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        tenant_id = str(uuid.uuid4())
        session.execute(
            text(
                """
                INSERT INTO tenants (id, slug, name, created_at, updated_at)
                VALUES (:id, :slug, :name, NOW(), NOW())
            """
            ),
            {"id": tenant_id, "slug": data["slug"], "name": data["name"]},
        )

        # Add creator as owner
        session.execute(
            text(
                """
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, 'owner', NOW())
            """
            ),
            {"tenant_id": tenant_id, "user_id": admin["user_id"]},
        )

        # Session commit is handled by the dependency
        return {"id": tenant_id, "slug": data["slug"], "name": data["name"]}

    except Exception as e:
        # Session rollback is handled by the dependency
        raise HTTPException(status_code=400, detail=f"Failed to create tenant: {str(e)}")


@router.get("/mine")
async def get_my_tenants(
    session: Session = Depends(get_db_session), admin=Depends(require_admin_auth)
) -> List[Dict[str, Any]]:
    """Get user's tenants."""
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Debug logging
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Getting tenants for user_id: {admin.get('user_id')}")

        result = session.execute(
            text(
                """
                SELECT t.id, t.slug, t.name, tm.role
                FROM tenants t
                JOIN tenant_memberships tm ON t.id = tm.tenant_id
                WHERE tm.user_id = :user_id AND t.deleted_at IS NULL
                ORDER BY t.name
            """
            ),
            {"user_id": admin["user_id"]},
        )

        tenants = [{"id": str(row[0]), "slug": row[1], "name": row[2], "role": row[3]} for row in result.fetchall()]
        logger.info(f"Found {len(tenants)} tenants for user_id {admin.get('user_id')}: {tenants}")
        return tenants

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tenants: {str(e)}")


@router.post("/{tenant_id}/members")
async def add_member(
    tenant_id: str,
    data: Dict[str, Any],
    request: Request,
    session: Session = Depends(get_db_session),
    admin=Depends(require_admin_auth),
) -> Dict[str, str]:
    """Add member to tenant."""
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Verify requester is admin/owner
        result = session.execute(
            text(
                """
                SELECT role FROM tenant_memberships
                WHERE tenant_id = :tenant_id AND user_id = :user_id
            """
            ),
            {"tenant_id": tenant_id, "user_id": admin["user_id"]},
        )
        membership = result.fetchone()
        if not membership or membership[0] not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Add new member
        session.execute(
            text(
                """
                INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
                VALUES (:tenant_id, :user_id, :role, NOW())
                ON CONFLICT (tenant_id, user_id) DO UPDATE SET role = :role
            """
            ),
            {"tenant_id": tenant_id, "user_id": data["user_id"], "role": data.get("role", "member")},
        )

        return {"status": "added"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add member: {str(e)}")


@router.delete("/{tenant_id}/members/{user_id}")
async def remove_member(
    tenant_id: str, user_id: int, session: Session = Depends(get_db_session), admin=Depends(require_admin_auth)
) -> Dict[str, str]:
    """Remove member from tenant."""
    if not session:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        # Verify requester is admin/owner
        result = session.execute(
            text(
                """
                SELECT role FROM tenant_memberships
                WHERE tenant_id = :tenant_id AND user_id = :user_id
            """
            ),
            {"tenant_id": tenant_id, "user_id": admin["user_id"]},
        )
        membership = result.fetchone()
        if not membership or membership[0] not in ["owner", "admin"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Cannot remove last owner
        result = session.execute(
            text(
                """
                SELECT COUNT(*) FROM tenant_memberships
                WHERE tenant_id = :tenant_id AND role = 'owner'
            """
            ),
            {"tenant_id": tenant_id},
        )
        owner_count = result.scalar()

        result = session.execute(
            text(
                """
                SELECT role FROM tenant_memberships
                WHERE tenant_id = :tenant_id AND user_id = :user_id
            """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
        target_role = result.scalar()

        if owner_count == 1 and target_role == "owner":
            raise HTTPException(status_code=400, detail="Cannot remove last owner")

        # Remove member
        session.execute(
            text(
                """
                DELETE FROM tenant_memberships
                WHERE tenant_id = :tenant_id AND user_id = :user_id
            """
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )

        return {"status": "removed"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove member: {str(e)}")
