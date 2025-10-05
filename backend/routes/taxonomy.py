"""
Tenant taxonomy management API routes.

Provides endpoints for managing tenant-scoped controlled vocabulary
for content types and tags.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from ..core.db_session import get_db_session_sync
from ..dependencies import get_tenant_context

router = APIRouter()
logger = logging.getLogger(__name__)


class TaxonomyEntry(BaseModel):
    """Model for a taxonomy entry."""

    key: str
    label: str
    synonyms: Optional[List[str]] = None
    active: bool = True


class TaxonomyResponse(BaseModel):
    """Response model for taxonomy listing."""

    entries: List[TaxonomyEntry]
    total: int
    tenant_id: str


class TaxonomyCreateRequest(BaseModel):
    """Request model for creating a taxonomy entry."""

    key: str
    label: str
    synonyms: Optional[List[str]] = None


class TaxonomyUpdateRequest(BaseModel):
    """Request model for updating a taxonomy entry."""

    label: Optional[str] = None
    synonyms: Optional[List[str]] = None
    active: Optional[bool] = None


@router.get("/taxonomy", response_model=TaxonomyResponse)
async def get_taxonomy(
    active_only: bool = True,
    tenant_context: Dict = Depends(get_tenant_context),
) -> TaxonomyResponse:
    """
    Get the taxonomy for the current tenant.

    Args:
        active_only: If True, only return active entries
        tenant_context: Tenant context from middleware

    Returns:
        Taxonomy response with all entries
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        with get_db_session_sync() as session:
            if session is None:
                raise HTTPException(status_code=503, detail="Database not available")

            # Set tenant context for RLS
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            # Query taxonomy
            query = """
                SELECT key, label, synonyms, active, created_at, updated_at
                FROM tenant_taxonomy
                WHERE tenant_id = :tenant_id
            """
            if active_only:
                query += " AND active = true"
            query += " ORDER BY label"

            rows = session.execute(text(query), {"tenant_id": tenant_id}).fetchall()

            entries = []
            for row in rows:
                entries.append(
                    TaxonomyEntry(
                        key=row[0],
                        label=row[1],
                        synonyms=row[2] if row[2] else [],
                        active=row[3],
                    )
                )

            return TaxonomyResponse(
                entries=entries,
                total=len(entries),
                tenant_id=tenant_id,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get taxonomy for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve taxonomy")


@router.post("/taxonomy", response_model=TaxonomyEntry)
async def create_taxonomy_entry(
    entry: TaxonomyCreateRequest,
    tenant_context: Dict = Depends(get_tenant_context),
) -> TaxonomyEntry:
    """
    Create a new taxonomy entry for the current tenant.

    Args:
        entry: Taxonomy entry data
        tenant_context: Tenant context from middleware

    Returns:
        Created taxonomy entry
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        with get_db_session_sync() as session:
            if session is None:
                raise HTTPException(status_code=503, detail="Database not available")

            # Set tenant context for RLS
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            # Check if key already exists
            existing = session.execute(
                text(
                    """
                    SELECT key FROM tenant_taxonomy
                    WHERE tenant_id = :tenant_id AND key = :key
                    """
                ),
                {"tenant_id": tenant_id, "key": entry.key},
            ).fetchone()

            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Taxonomy entry with key '{entry.key}' already exists",
                )

            # Insert new entry
            session.execute(
                text(
                    """
                    INSERT INTO tenant_taxonomy (tenant_id, key, label, synonyms, active)
                    VALUES (:tenant_id, :key, :label, :synonyms::jsonb, true)
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "key": entry.key,
                    "label": entry.label,
                    "synonyms": entry.synonyms if entry.synonyms else [],
                },
            )

            logger.info(f"Created taxonomy entry '{entry.key}' for tenant {tenant_id}")

            return TaxonomyEntry(
                key=entry.key,
                label=entry.label,
                synonyms=entry.synonyms if entry.synonyms else [],
                active=True,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create taxonomy entry for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create taxonomy entry")


@router.put("/taxonomy/{key}", response_model=TaxonomyEntry)
async def update_taxonomy_entry(
    key: str,
    update: TaxonomyUpdateRequest,
    tenant_context: Dict = Depends(get_tenant_context),
) -> TaxonomyEntry:
    """
    Update a taxonomy entry for the current tenant.

    Args:
        key: Taxonomy entry key
        update: Update data
        tenant_context: Tenant context from middleware

    Returns:
        Updated taxonomy entry
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        with get_db_session_sync() as session:
            if session is None:
                raise HTTPException(status_code=503, detail="Database not available")

            # Set tenant context for RLS
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            # Check if entry exists
            existing = session.execute(
                text(
                    """
                    SELECT key, label, synonyms, active
                    FROM tenant_taxonomy
                    WHERE tenant_id = :tenant_id AND key = :key
                    """
                ),
                {"tenant_id": tenant_id, "key": key},
            ).fetchone()

            if not existing:
                raise HTTPException(status_code=404, detail=f"Taxonomy entry '{key}' not found")

            # Build update query dynamically based on provided fields
            updates = []
            params = {"tenant_id": tenant_id, "key": key}

            if update.label is not None:
                updates.append("label = :label")
                params["label"] = update.label

            if update.synonyms is not None:
                updates.append("synonyms = :synonyms::jsonb")
                params["synonyms"] = update.synonyms

            if update.active is not None:
                updates.append("active = :active")
                params["active"] = update.active

            if not updates:
                # Nothing to update, return current entry
                return TaxonomyEntry(
                    key=existing[0],
                    label=existing[1],
                    synonyms=existing[2] if existing[2] else [],
                    active=existing[3],
                )

            # Execute update
            query = f"""
                UPDATE tenant_taxonomy
                SET {', '.join(updates)}
                WHERE tenant_id = :tenant_id AND key = :key
            """
            session.execute(text(query), params)

            # Fetch updated entry
            updated = session.execute(
                text(
                    """
                    SELECT key, label, synonyms, active
                    FROM tenant_taxonomy
                    WHERE tenant_id = :tenant_id AND key = :key
                    """
                ),
                {"tenant_id": tenant_id, "key": key},
            ).fetchone()

            logger.info(f"Updated taxonomy entry '{key}' for tenant {tenant_id}")

            return TaxonomyEntry(
                key=updated[0],
                label=updated[1],
                synonyms=updated[2] if updated[2] else [],
                active=updated[3],
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update taxonomy entry for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update taxonomy entry")


@router.delete("/taxonomy/{key}")
async def delete_taxonomy_entry(
    key: str,
    tenant_context: Dict = Depends(get_tenant_context),
) -> Dict:
    """
    Delete (deactivate) a taxonomy entry for the current tenant.

    Note: This soft-deletes by setting active=false to preserve data integrity.

    Args:
        key: Taxonomy entry key
        tenant_context: Tenant context from middleware

    Returns:
        Success message
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        with get_db_session_sync() as session:
            if session is None:
                raise HTTPException(status_code=503, detail="Database not available")

            # Set tenant context for RLS
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            # Check if entry exists
            existing = session.execute(
                text(
                    """
                    SELECT key FROM tenant_taxonomy
                    WHERE tenant_id = :tenant_id AND key = :key
                    """
                ),
                {"tenant_id": tenant_id, "key": key},
            ).fetchone()

            if not existing:
                raise HTTPException(status_code=404, detail=f"Taxonomy entry '{key}' not found")

            # Soft delete by setting active=false
            session.execute(
                text(
                    """
                    UPDATE tenant_taxonomy
                    SET active = false
                    WHERE tenant_id = :tenant_id AND key = :key
                    """
                ),
                {"tenant_id": tenant_id, "key": key},
            )

            logger.info(f"Deactivated taxonomy entry '{key}' for tenant {tenant_id}")

            return {
                "success": True,
                "message": f"Taxonomy entry '{key}' deactivated",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete taxonomy entry for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete taxonomy entry")
