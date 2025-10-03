import secrets
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.admin_auth import require_admin_auth
from backend.core.db_session import get_db_session

router = APIRouter(prefix="/api/admin/invitations", tags=["invitations"])


@router.post("/")
async def create_invitation(
    data: Dict[str, Any], session: Session = Depends(get_db_session), admin=Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Create tenant invitation."""
    # Verify requester can invite
    tenant_id = data["tenant_id"]
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
        raise HTTPException(status_code=403, detail="Cannot invite to this tenant")

    # Create invitation
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)

    result = session.execute(
        text(
            """
            INSERT INTO invitations (tenant_id, email, inviter_user_id, token, status, expires_at, created_at)
            VALUES (:tenant_id, :email, :inviter, :token, 'pending', :expires_at, NOW())
            RETURNING id
        """
        ),
        {
            "tenant_id": tenant_id,
            "email": data["email"],
            "inviter": admin["user_id"],
            "token": token,
            "expires_at": expires_at,
        },
    )
    invitation_id = result.scalar()

    return {
        "id": invitation_id,
        "token": token,
        "tenant_id": tenant_id,
        "email": data["email"],
        "expires_at": expires_at.isoformat(),
    }


@router.post("/accept")
async def accept_invitation(
    data: Dict[str, Any], session: Session = Depends(get_db_session), admin=Depends(require_admin_auth)
) -> Dict[str, str]:
    """Accept tenant invitation."""
    # Find valid invitation
    result = session.execute(
        text(
            """
            SELECT i.id, i.tenant_id, i.email, t.name
            FROM invitations i
            JOIN tenants t ON i.tenant_id = t.id
            WHERE i.token = :token
              AND i.status = 'pending'
              AND i.expires_at > NOW()
              AND t.deleted_at IS NULL
        """
        ),
        {"token": data["token"]},
    )
    invitation = result.fetchone()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    invitation_id, tenant_id, email, tenant_name = invitation

    # Verify email matches
    if email != admin.get("email", ""):
        raise HTTPException(status_code=403, detail="Invitation email mismatch")

    # Add user to tenant
    session.execute(
        text(
            """
            INSERT INTO tenant_memberships (tenant_id, user_id, role, created_at)
            VALUES (:tenant_id, :user_id, 'member', NOW())
            ON CONFLICT (tenant_id, user_id) DO NOTHING
        """
        ),
        {"tenant_id": tenant_id, "user_id": admin["user_id"]},
    )

    # Mark invitation as accepted
    session.execute(
        text(
            """
            UPDATE invitations
            SET status = 'accepted'
            WHERE id = :id
        """
        ),
        {"id": invitation_id},
    )

    return {"status": "accepted", "tenant_id": str(tenant_id), "tenant_name": tenant_name}
