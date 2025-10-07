"""
Tenant taxonomy management API routes.

Provides endpoints for managing tenant-scoped controlled vocabulary
for content types and tags.
"""

import json
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
                    VALUES (:tenant_id, :key, :label, CAST(:synonyms AS jsonb), true)
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "key": entry.key,
                    "label": entry.label,
                    "synonyms": json.dumps(entry.synonyms if entry.synonyms else []),
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
                updates.append("synonyms = CAST(:synonyms AS jsonb)")
                params["synonyms"] = json.dumps(update.synonyms)

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


@router.post("/taxonomy/bootstrap")
async def bootstrap_taxonomy(
    request: Dict,
    tenant_context: Dict = Depends(get_tenant_context),
) -> Dict:
    """
    Bootstrap tenant taxonomy from a template.

    This is typically called during tenant onboarding. It creates initial
    taxonomy entries based on an industry-specific template.

    Args:
        template_key: Template identifier (software, legal, medical, marketing, or empty)
        force: If True, delete existing entries before bootstrapping
        tenant_context: Tenant context from middleware

    Returns:
        Dictionary with created entries count
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")

    # Extract template key and force flag from request body
    template_key = request.get("template")
    force = request.get("force", False)  # Default to False for backwards compatibility

    if not template_key:
        raise HTTPException(status_code=400, detail="Template key required in request body")

    try:
        # Import template module
        from ..core.taxonomy_templates import get_template

        # Get template
        try:
            template_entries = get_template(template_key)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check if tenant already has taxonomy entries
        with get_db_session_sync() as session:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            existing = session.execute(
                text("SELECT COUNT(*) FROM tenant_taxonomy WHERE tenant_id = :tid"),
                {"tid": tenant_id}
            ).scalar()

            if existing > 0:
                if not force:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Tenant already has {existing} taxonomy entries. Use force=true to replace them."
                    )
                else:
                    # Delete existing entries before bootstrapping
                    session.execute(
                        text("DELETE FROM tenant_taxonomy WHERE tenant_id = :tid"),
                        {"tid": tenant_id}
                    )
                    session.commit()
                    logger.info(f"Deleted {existing} existing taxonomy entries for tenant {tenant_id} (force re-bootstrap)")

        # Create entries from template by inserting directly into database
        created_count = 0
        with get_db_session_sync() as session:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            for entry in template_entries:
                try:
                    # Insert directly to avoid dependency injection issues
                    result = session.execute(
                        text("""
                            INSERT INTO tenant_taxonomy (tenant_id, key, label, synonyms, active)
                            VALUES (:tenant_id, :key, :label, CAST(:syn_json AS jsonb), true)
                            ON CONFLICT (tenant_id, key) DO NOTHING
                            RETURNING key
                        """),
                        {
                            "tenant_id": tenant_id,
                            "key": entry["key"],
                            "label": entry["label"],
                            "syn_json": json.dumps(entry.get("synonyms", [])),
                        }
                    )
                    # Only count if row was actually inserted (not skipped due to conflict)
                    if result.fetchone():
                        created_count += 1
                        logger.debug(f"Created taxonomy entry '{entry['key']}' for tenant {tenant_id}")
                except Exception as e:
                    logger.error(f"Failed to create taxonomy entry '{entry.get('key')}': {e}")
                    continue

            # Commit all changes
            session.commit()

        logger.info(f"Bootstrapped taxonomy for tenant {tenant_id} with template '{template_key}': {created_count} entries")

        return {
            "template": template_key,
            "entries_created": created_count,
            "tenant_id": str(tenant_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bootstrap taxonomy for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to bootstrap taxonomy")


@router.get("/taxonomy/templates")
async def list_taxonomy_templates() -> Dict:
    """
    List available taxonomy templates for bootstrapping.

    Returns:
        Dictionary of available templates with metadata
    """
    try:
        from ..core.taxonomy_templates import list_templates
        return {"templates": list_templates()}
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to list templates")


@router.get("/taxonomy/bootstrap/detect")
async def detect_bootstrap_template(
    tenant_context: Dict = Depends(get_tenant_context),
) -> Dict:
    """
    Detect which bootstrap template was used based on existing taxonomy entries.

    Compares existing category keys with each template to find the best match.

    Returns:
        Dictionary with detected template key and confidence score
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID required")

    try:
        from ..core.taxonomy_templates import get_template

        # Get existing taxonomy keys
        with get_db_session_sync() as session:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            result = session.execute(
                text("SELECT key FROM tenant_taxonomy WHERE tenant_id = :tid AND active = true"),
                {"tid": tenant_id}
            )
            existing_keys = {row[0] for row in result.fetchall()}

        if not existing_keys:
            return {"template": None, "confidence": 0.0, "has_entries": False}

        # Compare with each template
        templates = ["software", "legal", "medical", "marketing", "empty"]
        best_match = None
        best_score = 0.0

        for template_key in templates:
            try:
                template_entries = get_template(template_key)
                template_keys = {entry["key"] for entry in template_entries}

                # Calculate Jaccard similarity (intersection / union)
                if not template_keys:  # empty template
                    score = 0.0
                else:
                    intersection = len(existing_keys & template_keys)
                    union = len(existing_keys | template_keys)
                    score = intersection / union if union > 0 else 0.0

                if score > best_score:
                    best_score = score
                    best_match = template_key

            except KeyError:
                continue

        return {
            "template": best_match if best_score > 0.5 else None,  # Only return if >50% match
            "confidence": best_score,
            "has_entries": True,
            "entry_count": len(existing_keys)
        }

    except Exception as e:
        logger.error(f"Failed to detect bootstrap template: {e}")
        raise HTTPException(status_code=500, detail="Failed to detect template")


@router.get("/taxonomy/tags/autocomplete")
async def get_tag_autocomplete(
    q: str = "",
    limit: int = 10,
    tenant_context: Dict = Depends(get_tenant_context),
) -> Dict:
    """
    Get tag autocomplete suggestions from existing tags.

    Args:
        q: Search query (case-insensitive substring match)
        limit: Maximum results (default 10, max 50)
        tenant_context: Tenant context from middleware

    Returns:
        Dictionary with suggestions list
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        from ..core.tag_manager import tag_manager

        # Limit to max 50
        limit = min(limit, 50)

        suggestions = tag_manager.get_autocomplete_suggestions(
            tenant_id=tenant_id,
            query=q,
            limit=limit,
        )

        return {"suggestions": suggestions}

    except Exception as e:
        logger.error(f"Failed to get tag autocomplete: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tag autocomplete")


@router.get("/taxonomy/analytics")
async def get_tag_analytics(
    tenant_context: Dict = Depends(get_tenant_context),
) -> Dict:
    """
    Get comprehensive tag analytics for taxonomy management.

    Returns:
        Dictionary with popular_tags, orphans, co_occurring, and coverage metrics
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        from ..core.tag_manager import tag_manager

        analytics = tag_manager.get_tag_analytics(tenant_id=tenant_id)

        return analytics

    except Exception as e:
        logger.error(f"Failed to get tag analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get tag analytics")


class TagPromotionRequest(BaseModel):
    """Request model for promoting a tag to official taxonomy."""

    label: Optional[str] = None
    synonyms: Optional[List[str]] = None
    regex: Optional[List[str]] = None
    description: Optional[str] = None


@router.post("/taxonomy/tags/{tag}/promote")
async def promote_tag(
    tag: str,
    request: TagPromotionRequest,
    tenant_context: Dict = Depends(get_tenant_context),
) -> Dict:
    """
    Promote a user-created tag to official taxonomy entry.

    Args:
        tag: Tag to promote
        request: Promotion metadata (label, synonyms, regex, description)
        tenant_context: Tenant context from middleware

    Returns:
        Success message
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        from ..core.tag_manager import tag_manager

        metadata = {
            "label": request.label,
            "synonyms": request.synonyms or [],
            "regex": request.regex or [],
            "description": request.description or "",
        }

        success = tag_manager.promote_tag_to_official(
            tenant_id=tenant_id,
            tag=tag,
            metadata=metadata,
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to promote tag '{tag}' - it may already exist in taxonomy",
            )

        logger.info(f"Promoted tag '{tag}' to official taxonomy for tenant {tenant_id}")

        return {
            "success": True,
            "message": f"Tag '{tag}' promoted to official taxonomy",
            "tag": tag,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to promote tag: {e}")
        raise HTTPException(status_code=500, detail="Failed to promote tag")
