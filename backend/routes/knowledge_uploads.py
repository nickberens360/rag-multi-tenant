"""
Tenant-aware knowledge upload endpoints.

This module provides endpoints for uploading knowledge files within tenant scope:
- Multipart file uploads with tenant isolation
- Upload status tracking per tenant
- File validation and security checks
"""

import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..core.knowledge_index_db import KnowledgeIndexDB
from ..dependencies import get_tenant_context

router = APIRouter()
logger = logging.getLogger(__name__)

# File upload validation settings
ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".json", ".html", ".docx", ".csv", ".xml"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILES_PER_UPLOAD = 10


class UploadResponse(BaseModel):
    """Response model for file upload."""

    id: str
    filename: str
    path: str
    size: int
    status: str
    tenant_id: str


class UploadStatusResponse(BaseModel):
    """Response model for upload status."""

    uploads: List[Dict]
    total: int
    tenant_id: str


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file for security and type constraints."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Check file extension
    file_path = Path(file.filename)
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Check for suspicious filename patterns
    if ".." in file.filename or "/" in file.filename or "\\" in file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Note: File size will be checked during streaming read


def ensure_tenant_directory(tenant_slug: str) -> Path:
    """Ensure tenant directory exists and return the path."""
    tenant_dir = Path("backend/knowledge/tenants") / tenant_slug / "documents"
    tenant_dir.mkdir(parents=True, exist_ok=True)
    return tenant_dir


def _reindex_file_task(path: str, tenant_id: Optional[str], retriever: object) -> None:
    """Background task to reindex a single file and update DB status."""
    try:
        from ..core.knowledge_index_db import KnowledgeIndexDB

        db = KnowledgeIndexDB()

        ok = False
        try:
            # Run reindex via unified retriever
            ok = bool(getattr(retriever, "reindex_file")(path))  # type: ignore[misc]
        except Exception as e:  # pragma: no cover - background task
            logger.error(f"Background reindex failed for {path}: {e}")
            ok = False

        if ok:
            # Best-effort compute hash and vector_count
            try:
                from pathlib import Path as _P

                file_hash = getattr(retriever, "content_indexer").compute_file_hash(_P(path))  # type: ignore[attr-defined]
            except Exception:
                file_hash = None

            try:
                vcount = getattr(retriever, "semantic_searcher").get_count(where={"source": path})  # type: ignore[attr-defined]
            except Exception:
                vcount = None

            try:
                db.update_indexed(path, file_hash=file_hash, chunk_count=None, vector_count=vcount, tenant_id=tenant_id)
            except Exception:
                # Non-fatal
                pass
            logger.info(f"Background reindex complete: {path}")
        else:
            try:
                db.record_error(path, error="Reindex failed", tenant_id=tenant_id)
            except Exception:
                pass
            logger.warning(f"Background reindex did not complete for: {path}")
    except Exception as e:  # pragma: no cover
        logger.error(f"Background reindex task crashed for {path}: {e}")


@router.post("/knowledge/uploads")
async def upload_knowledge_files(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    path_prefix: Optional[str] = Form(None),
    index_now: bool = Form(True),
    metadata_content_type: Optional[str] = Form(None),
    metadata_tags: Optional[str] = Form(None),
    tenant_context: Dict = Depends(get_tenant_context),
) -> JSONResponse:
    """
    Upload knowledge files for a specific tenant.

    Args:
        files: List of files to upload (multipart/form-data)
        path_prefix: Optional subdirectory within tenant documents folder
        index_now: Whether to trigger immediate indexing (default: True)
        metadata_content_type: Optional manual content type for uploaded files
        metadata_tags: Optional comma-separated tags for uploaded files
        tenant_context: Tenant context from middleware

    Returns:
        JSON response with upload results
    """
    tenant_id = tenant_context.get("tenant_id")
    tenant_slug = tenant_context.get("tenant_slug")

    if not tenant_id or not tenant_slug:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(status_code=400, detail=f"Too many files. Maximum {MAX_FILES_PER_UPLOAD} files per upload.")

    # Ensure tenant directory exists
    tenant_dir = ensure_tenant_directory(tenant_slug)

    # Add optional path prefix
    if path_prefix:
        # Sanitize path prefix
        path_prefix = path_prefix.strip("/\\").replace("..", "")
        if path_prefix:
            tenant_dir = tenant_dir / path_prefix
            tenant_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = []
    db = KnowledgeIndexDB()

    for file in files:
        try:
            # Validate file
            validate_file(file)

            # Generate unique filename to prevent conflicts
            file_id = str(uuid.uuid4())
            file_path = Path(file.filename)
            safe_filename = f"{file_id}_{file_path.name}"
            full_path = tenant_dir / safe_filename

            # Read and validate file size
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
                )

            # Write file to tenant directory
            with open(full_path, "wb") as f:
                f.write(content)

            # Record in database (discovered)
            db.upsert_file(path=str(full_path), size=len(content), tenant_id=tenant_id, scope="tenant")

            # Set manual metadata if provided
            if metadata_content_type or metadata_tags:
                from sqlalchemy import text
                from ..core.db_session import get_db_session_sync

                try:
                    with get_db_session_sync() as session:
                        if session is not None:
                            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                            # Parse tags from CSV
                            tags_list = []
                            if metadata_tags:
                                tags_list = [t.strip() for t in metadata_tags.split(",") if t.strip()]

                            session.execute(
                                text(
                                    """
                                    UPDATE knowledge_files
                                    SET manual_content_type = :content_type,
                                        manual_tags = :tags::jsonb,
                                        metadata_provenance = 'manual',
                                        metadata_updated_at = NOW(),
                                        metadata_version = metadata_version + 1
                                    WHERE path = :path AND tenant_id = :tenant_id
                                    """
                                ),
                                {
                                    "path": str(full_path),
                                    "tenant_id": tenant_id,
                                    "content_type": metadata_content_type,
                                    "tags": tags_list,
                                },
                            )
                            logger.info(f"Set manual metadata for {full_path}: type={metadata_content_type}, tags={tags_list}")
                except Exception as e:
                    logger.warning(f"Failed to set manual metadata for {full_path}: {e}")
            else:
                # Queue background inference if no manual metadata provided
                try:
                    from ..core.metadata_inference import infer_metadata_background

                    background_tasks.add_task(infer_metadata_background, str(full_path), tenant_id)
                    logger.info(f"Queued background metadata inference for {full_path}")
                except Exception as e:
                    logger.warning(f"Failed to queue metadata inference for {full_path}: {e}")

            uploaded_files.append(
                UploadResponse(
                    id=file_id,
                    filename=file.filename,
                    path=str(full_path),
                    size=len(content),
                    status="uploaded",
                    tenant_id=tenant_id,
                )
            )

            logger.info(f"Uploaded file {file.filename} for tenant {tenant_slug} at {full_path}")

            # Trigger background reindex if requested
            try:
                if index_now and hasattr(request.app.state, "unified_retriever") and request.app.state.unified_retriever is not None:
                    background_tasks.add_task(_reindex_file_task, str(full_path), tenant_id, request.app.state.unified_retriever)
                    logger.info(f"Queued background reindex for {full_path}")
            except Exception as e:
                logger.warning(f"Failed to queue background reindex for {full_path}: {e}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload file {file.filename}: {e}")
            # Clean up any partial files
            if "full_path" in locals() and full_path.exists():
                full_path.unlink()
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}")

    return JSONResponse(
        content={
            "success": True,
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": [file.dict() for file in uploaded_files],
            "tenant_id": tenant_id,
        }
    )


@router.get("/knowledge/uploads/status")
async def get_upload_status(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    tenant_context: Dict = Depends(get_tenant_context),
) -> UploadStatusResponse:
    """
    Get upload status for tenant's knowledge files.

    Args:
        limit: Maximum number of records to return
        offset: Offset for pagination
        status: Optional filter by status
        tenant_context: Tenant context from middleware

    Returns:
        Upload status response with tenant-scoped files
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        db = KnowledgeIndexDB()
        # SECURITY: list_files automatically filters by tenant_id (tenant-only, NO shared)
        files = db.list_files(
            status=status,
            limit=limit,
            offset=offset,
            tenant_id=tenant_id,
        )

        # Convert to upload-friendly format
        uploads = []
        for file_record in files:
            uploads.append(
                {
                    "id": file_record["id"],
                    "filename": file_record["filename"],
                    "path": file_record["path"],
                    "size": file_record["size"],
                    "status": file_record["status"],
                    "uploaded_at": str(file_record["discovered_at"]) if file_record["discovered_at"] else None,
                    "indexed_at": str(file_record["indexed_at"]) if file_record["indexed_at"] else None,
                    "chunk_count": file_record["chunk_count"],
                    "vector_count": file_record["vector_count"],
                    "last_error": file_record["last_error"],
                }
            )

        return UploadStatusResponse(
            uploads=uploads,
            total=len(uploads),
            tenant_id=tenant_id,
        )

    except Exception as e:
        logger.error(f"Failed to get upload status for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve upload status")


@router.delete("/knowledge/uploads/{file_id}")
async def delete_uploaded_file(
    file_id: str,
    tenant_context: Dict = Depends(get_tenant_context),
) -> JSONResponse:
    """
    Delete an uploaded file for the current tenant.

    Args:
        file_id: ID of the file to delete
        tenant_context: Tenant context from middleware

    Returns:
        JSON response confirming deletion
    """
    tenant_id = tenant_context.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        db = KnowledgeIndexDB()

        # SECURITY: Find the file record (tenant-only, NO shared)
        files = db.list_files(tenant_id=tenant_id)
        file_record = None
        for f in files:
            if str(f["id"]) == file_id:
                file_record = f
                break

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        # Delete the physical file
        file_path = Path(file_record["path"])
        if file_path.exists():
            file_path.unlink()

        # Note: Database record will be cleaned up by sync operations
        # For now, we'll update status to indicate deletion
        db.update_status(file_record["path"], status="deleted", tenant_id=tenant_id)

        logger.info(f"Deleted file {file_record['filename']} for tenant {tenant_id}")

        return JSONResponse(
            content={
                "success": True,
                "message": f"File {file_record['filename']} deleted successfully",
                "file_id": file_id,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete file {file_id} for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@router.get("/knowledge/uploads/quota")
async def get_upload_quota(
    tenant_context: Dict = Depends(get_tenant_context),
) -> JSONResponse:
    """
    Get upload quota information for the current tenant.

    Args:
        tenant_context: Tenant context from middleware

    Returns:
        Quota information including usage and limits
    """
    tenant_id = tenant_context.get("tenant_id")
    tenant_slug = tenant_context.get("tenant_slug")

    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant context not available")

    try:
        # Calculate current usage
        tenant_dir = Path("backend/knowledge/tenants") / tenant_slug / "documents"
        total_size = 0
        file_count = 0

        if tenant_dir.exists():
            for file_path in tenant_dir.rglob("*"):
                if file_path.is_file():
                    file_count += 1
                    total_size += file_path.stat().st_size

        # TODO: Make these configurable per tenant
        max_total_size = 500 * 1024 * 1024  # 500MB default
        max_file_count = 1000

        return JSONResponse(
            content={
                "tenant_id": tenant_id,
                "current_usage": {
                    "total_size_bytes": total_size,
                    "file_count": file_count,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                },
                "limits": {
                    "max_total_size_bytes": max_total_size,
                    "max_file_count": max_file_count,
                    "max_file_size_bytes": MAX_FILE_SIZE,
                    "allowed_extensions": list(ALLOWED_EXTENSIONS),
                    "max_files_per_upload": MAX_FILES_PER_UPLOAD,
                },
                "available": {
                    "size_bytes": max(0, max_total_size - total_size),
                    "file_count": max(0, max_file_count - file_count),
                },
            }
        )

    except Exception as e:
        logger.error(f"Failed to get quota for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve quota information")
