"""
Admin knowledge consistency and reconciliation routes.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..core.admin_auth import require_admin_auth
from ..core.config_v2 import AppConfig
from ..core.knowledge_index_db import KnowledgeIndexDB
from ..core.knowledge_state_sync import KnowledgeStateSync

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-knowledge"], dependencies=[Depends(require_admin_auth)])


def _get_sync(request: Request) -> KnowledgeStateSync:
    if not hasattr(request.app.state, "unified_retriever") or request.app.state.unified_retriever is None:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")
    retriever = request.app.state.unified_retriever

    # Prefer semantic_searcher.persist_dir if available
    persist_dir = os.getenv("UNIFIED_PERSIST_DIR", "backend/.unified_chroma")
    try:
        ss = getattr(retriever, "semantic_searcher", None)
        if ss and getattr(ss, "persist_dir", None):
            persist_dir = ss.persist_dir
    except Exception:
        pass

    # Index dirs from config (tenant content only; exclude public)
    index_dirs = AppConfig.get_rag_index_dirs() or ["backend/knowledge"]
    return KnowledgeStateSync(retriever, persist_dir=persist_dir, index_dirs=index_dirs)


class ReconcileRequest(BaseModel):
    dry_run: bool = True
    allow_deletes: bool = False
    limit: Optional[int] = None
    paths: Optional[List[str]] = None


@router.get("/knowledge/consistency")
async def get_knowledge_consistency(request: Request, sample: int = Query(50, ge=1, le=500)) -> Dict[str, Any]:
    """Return consistency summary and samples of mismatches."""
    try:
        sync = _get_sync(request)
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)
        summary, diff = sync.validate(tenant_id=tenant_id, tenant_slug=tenant_slug)

        # Final safety filter by tenant slug to avoid any cross-tenant bleed
        def _filter_paths(paths: List[str]) -> List[str]:
            if not tenant_slug:
                return paths
            # Use relative path format (no leading slash) since paths are like "backend/knowledge/tenants/..."
            marker = f"tenants/{tenant_slug}/"
            default_slug = os.getenv("DEFAULT_TENANT_SLUG", "default")
            if tenant_slug == default_slug:
                # Default tenant can include top-level files not under tenants/
                return [p for p in paths if ("tenants/" not in p) or (marker in p)]
            return [p for p in paths if marker in p]

        # Truncate lists for response brevity
        def _sample(lst: List[str]) -> Dict[str, Any]:
            flist = _filter_paths(lst)
            return {"total": len(flist), "sample": flist[:sample]}

        return {
            "summary": summary.__dict__,
            "diff": {
                "discovered_not_indexed": _sample(diff.get("discovered_not_indexed", [])),
                "changed_files": _sample(diff.get("changed_files", [])),
                "vector_orphans": _sample(diff.get("vector_orphans", [])),
                "tracked_but_missing": _sample(diff.get("tracked_but_missing", [])),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consistency check failed: {e}")
        raise HTTPException(status_code=500, detail="Consistency check failed")


@router.post("/knowledge/reconcile")
async def reconcile_knowledge(request: Request, payload: ReconcileRequest = Body(...)) -> Dict[str, Any]:
    """Run reconciliation (dry-run by default)."""
    try:
        sync = _get_sync(request)
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)
        result = sync.reconcile(
            dry_run=payload.dry_run,
            allow_deletes=payload.allow_deletes,
            paths=payload.paths,
            limit=payload.limit,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reconcile failed: {e}")
        raise HTTPException(status_code=500, detail="Reconcile failed")


@router.get("/knowledge/consistency/list")
async def get_knowledge_consistency_list(
    request: Request,
    kind: str = Query(
        ..., description="List kind: discovered_not_indexed | changed_files | vector_orphans | tracked_but_missing"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
) -> Dict[str, Any]:
    """Paginated list for a specific mismatch kind."""
    try:
        sync = _get_sync(request)
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)
        _summary, diff = sync.validate(tenant_id=tenant_id, tenant_slug=tenant_slug)

        valid = {
            "discovered_not_indexed": diff.get("discovered_not_indexed", []),
            "changed_files": diff.get("changed_files", []),
            "vector_orphans": diff.get("vector_orphans", []),
            "tracked_but_missing": diff.get("tracked_but_missing", []),
        }
        if kind not in valid:
            raise HTTPException(status_code=400, detail="Invalid kind parameter")
        items = valid[kind]
        # Final safety filter by tenant slug
        if tenant_slug:
            # Use relative path format (no leading slash) since paths are like "backend/knowledge/tenants/..."
            marker = f"tenants/{tenant_slug}/"
            default_slug = os.getenv("DEFAULT_TENANT_SLUG", "default")
            if tenant_slug == default_slug:
                # Default tenant: include files that don't have "tenants/" OR have "tenants/default/"
                items = [p for p in items if ("tenants/" not in p) or (marker in p)]
            else:
                # Non-default tenant: only include files with "tenants/{slug}/"
                items = [p for p in items if marker in p]
        total = len(items)
        page_items = items[offset : offset + limit]
        return {"items": page_items, "total": total, "offset": offset, "limit": limit}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Consistency list failed: {e}")
        raise HTTPException(status_code=500, detail="Consistency list failed")


@router.get("/knowledge/files/status")
async def list_knowledge_files(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """List knowledge files from the metadata DB. Seeds DB on first call."""
    try:
        # SECURITY: Seed DB if empty; scope to tenant context (tenant-only, NO shared)
        tenant_id = getattr(request.state, "tenant_id", None)
        tenant_slug = getattr(request.state, "tenant_slug", None)
        db = KnowledgeIndexDB()
        rows = db.list_files_with_metadata(status=status, limit=limit, offset=offset, tenant_id=tenant_id)
        if not rows:
            sync = _get_sync(request)
            sync.scan_filesystem(tenant_id=tenant_id, tenant_slug=tenant_slug)
            # Refresh
            rows = db.list_files_with_metadata(status=status, limit=limit, offset=offset, tenant_id=tenant_id)

        # Safety filter by path to avoid any legacy rows mis-attributed to this tenant
        if tenant_slug:
            tenant_path_marker = f"/tenants/{tenant_slug}/"
            rows = [r for r in rows if isinstance(r, dict) and tenant_path_marker in (r.get("path") or "")]
        return {"files": rows, "total": len(rows)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list knowledge files: {e}")
        raise HTTPException(status_code=500, detail="Failed to list knowledge files")


class ReindexFileRequest(BaseModel):
    path: str


@router.post("/knowledge/reindex-file")
async def reindex_single_file(request: Request, payload: ReindexFileRequest) -> Dict[str, Any]:
    try:
        sync = _get_sync(request)
        ok = sync.unified_retriever.reindex_file(payload.path)
        if not ok:
            raise HTTPException(status_code=500, detail="Reindex failed")
        # Best-effort DB update
        try:
            db = KnowledgeIndexDB()
            file_hash = sync.unified_retriever.content_indexer.compute_file_hash(Path(payload.path))
            db.update_indexed(
                payload.path,
                file_hash=file_hash,
                chunk_count=None,
                vector_count=None,
                tenant_id=getattr(request.state, "tenant_id", None),
            )
        except Exception:
            pass
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reindex file: {e}")
        raise HTTPException(status_code=500, detail="Failed to reindex file")


@router.get("/knowledge/health")
async def knowledge_health(request: Request) -> Dict[str, Any]:
    """Basic health check summarizing consistency status."""
    try:
        sync = _get_sync(request)
        summary, _ = sync.validate(
            tenant_id=getattr(request.state, "tenant_id", None),
            tenant_slug=getattr(request.state, "tenant_slug", None),
        )
        healthy = summary.discovered_not_indexed == 0 and summary.changed_files == 0 and summary.vector_orphans == 0

        # Read last reconcile timestamp if available
        last_reconcile_at: Optional[str] = None
        try:
            marker = Path(sync.persist_dir) / ".last_reconcile"
            if marker.exists():
                last_reconcile_at = marker.read_text(encoding="utf-8").strip()
        except Exception:
            pass

        return {
            "ok": healthy,
            "summary": summary.__dict__,
            "last_reconcile_at": last_reconcile_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")
