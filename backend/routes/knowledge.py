"""
Knowledge base management API routes.

Provides endpoints for:
- Viewing indexed documents
- Managing knowledge base content
- Document statistics and analytics
"""

import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from ..core.admin_auth import require_admin_auth
from ..dependencies import get_tenant_context

logger = logging.getLogger(__name__)
router = APIRouter()


class IndexedDocument(BaseModel):
    """Model for indexed document data."""

    id: str
    source: str
    content_preview: str
    content_type: str
    metadata: dict
    word_count: int


class IndexedDocumentsResponse(BaseModel):
    """Response model for indexed documents listing."""

    documents: List[IndexedDocument]
    total_count: int
    collection_name: str
    embedding_model: str


class KnowledgeStats(BaseModel):
    """Model for knowledge base statistics."""

    total_documents: int
    total_chunks: int
    unique_sources: int
    content_types: dict
    last_updated: Optional[str] = None


class SourceUpdateRequest(BaseModel):
    """Model for updating a source."""

    content_type: Optional[str] = None  # For backward compatibility
    manual_content_type: Optional[str] = None
    manual_tags: Optional[List[str]] = None


class MetadataInferenceRequest(BaseModel):
    """Request model for triggering metadata inference."""

    paths: Optional[List[str]] = None  # Specific paths to infer; if None, infer all files without metadata
    dry_run: bool = False  # If True, only return what would be inferred without updating
    limit: Optional[int] = None  # Maximum number of files to process


@router.get("/knowledge/documents", response_model=IndexedDocumentsResponse)
async def get_indexed_documents(
    request: Request,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    source_filter: Optional[str] = Query(None, description="Filter by source path"),
):
    """
    Get indexed documents from the knowledge base.

    Args:
        limit: Maximum number of documents to return
        offset: Offset for pagination
        content_type: Optional filter by content type
        source_filter: Optional filter by source path
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Build query filter (tenant-scoped). We require an active tenant context
        # and do not include shared/unscoped documents on this admin view.
        where_clause = {}
        tid = getattr(request.state, "tenant_id", None)
        tslug: Optional[str] = None
        try:
            tslug = request.path_params.get("tenant")  # type: ignore[attr-defined]
        except Exception:
            tslug = getattr(request.state, "tenant_slug", None)

        # Prefer filtering by tenant_id; fall back to tenant_slug only if id unavailable
        if tid:
            where_clause["tenant_id"] = tid
        elif tslug:
            where_clause["tenant_slug"] = tslug
        else:
            # No tenant context — return empty result to avoid cross-tenant leakage
            return IndexedDocumentsResponse(
                documents=[],
                total_count=0,
                collection_name="unified_knowledge",
                embedding_model="text-embedding-3-small",
            )

        if content_type:
            where_clause["content_type"] = content_type
        if source_filter:
            where_clause["source"] = {"$contains": source_filter}

        # Get documents using proper encapsulated method
        try:
            result_docs = retriever.semantic_searcher.get_documents(
                where=where_clause if where_clause else None, limit=limit, offset=offset
            )
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            raise HTTPException(status_code=503, detail="Failed to retrieve documents")

        # Strict server-side tenant filter as a safety net in case the underlying
        # vector store's metadata filter behaves loosely in some versions.
        documents = []
        for doc in result_docs:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            doc_id = doc.get("id", "")

            # Enforce tenant isolation at the row level
            doc_tid = metadata.get("tenant_id")
            doc_tslug = metadata.get("tenant_slug")
            if tid and (not doc_tid or str(doc_tid) != str(tid)):
                continue
            if (not tid) and tslug and (not doc_tslug or str(doc_tslug) != str(tslug)):
                continue

            # Create content preview (first 200 characters)
            preview = content[:200] + "..." if len(content) > 200 else content

            documents.append(
                IndexedDocument(
                    id=doc_id,
                    source=metadata.get("source", "unknown"),
                    content_preview=preview,
                    content_type=metadata.get("content_type", "unknown"),
                    metadata=metadata,
                    word_count=len(content.split()) if content else 0,
                )
            )

        # Use the strict filtered count for accuracy on this view
        total_count = len(documents)

        # Get collection info
        collection_name = "unified_knowledge"  # This is hardcoded in SemanticSearcher
        embedding_model = "text-embedding-3-small"  # Default embedding model from config

        return IndexedDocumentsResponse(
            documents=documents,
            total_count=total_count,
            collection_name=collection_name,
            embedding_model=embedding_model,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_indexed_documents: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/knowledge/stats", response_model=KnowledgeStats)
async def get_knowledge_stats(request: Request):
    """
    Get statistics about the knowledge base.
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get tenant context and fetch only tenant documents
        try:
            from ..core.config_v2 import AppConfig
        except Exception:
            AppConfig = None  # type: ignore

        tid = getattr(request.state, "tenant_id", None)
        if not tid and AppConfig is not None:
            tid = getattr(AppConfig, "DEFAULT_TENANT_ID", None)

        where = {"tenant_id": tid} if tid else None
        # Get all documents metadata using encapsulated method, tenant-only
        all_docs = retriever.semantic_searcher.get_documents(where=where, limit=100000)

        if not all_docs:
            return KnowledgeStats(total_documents=0, total_chunks=0, unique_sources=0, content_types={})

        # Calculate statistics
        total_chunks = len(all_docs)

        # Count unique sources and content types
        sources = set()
        content_types = {}

        for doc in all_docs:
            metadata = doc.get("metadata", {})
            if metadata:
                source = metadata.get("source", "unknown")
                sources.add(source)

                ct = metadata.get("content_type", "unknown")
                if ct and ct != "unknown":
                    # Split comma-separated content types and process individually
                    individual_types = [
                        t.strip()
                        for t in ct.split(",")
                        if t.strip()
                        and not t.strip().startswith("based on")
                        and not t.strip().startswith("the main topics")
                    ]
                    for content_type in individual_types:
                        # Skip overly descriptive text, keep only core content type words
                        if (
                            len(content_type) > 50
                            or "based on" in content_type.lower()
                            or "main topics" in content_type.lower()
                        ):
                            continue
                        content_types[content_type] = content_types.get(content_type, 0) + 1
                else:
                    content_types["unknown"] = content_types.get("unknown", 0) + 1

        return KnowledgeStats(
            total_documents=total_chunks,
            total_chunks=total_chunks,
            unique_sources=len(sources),
            content_types=content_types,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_knowledge_stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/knowledge/sources")
async def get_knowledge_sources(request: Request):
    """
    Get list of all unique sources in the knowledge base.
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get all documents metadata using encapsulated method (tenant-only)
        tid = getattr(request.state, "tenant_id", None)
        where = {"tenant_id": tid} if tid else None
        if where is None:
            # Fallback to tenant_slug from path params
            try:
                tslug = request.path_params.get("tenant")  # type: ignore[attr-defined]
                if tslug:
                    where = {"tenant_slug": tslug}
            except Exception:
                pass
        all_docs = retriever.semantic_searcher.get_documents(where=where, limit=100000)

        if not all_docs:
            return {"sources": [], "total": 0}

        # Collect unique sources with counts
        source_counts = {}

        for doc in all_docs:
            metadata = doc.get("metadata", {})
            if metadata:
                source = metadata.get("source", "unknown")
                content_type = metadata.get("content_type", "unknown")

                if source not in source_counts:
                    # Provide both full path and display path for frontend
                    display_path = source
                    if source.startswith("backend/knowledge/"):
                        display_path = source.replace("backend/knowledge/", "")
                    elif source.startswith("public/"):
                        display_path = source.replace("public/", "")

                    source_counts[source] = {
                        "path": source,  # Full path for backend operations
                        "display_path": display_path,  # Clean path for frontend display
                        "content_type": content_type,
                        "chunk_count": 0,
                    }
                source_counts[source]["chunk_count"] += 1

        # Convert to list and sort by path
        sources = list(source_counts.values())
        sources.sort(key=lambda x: x["path"])

        return {"sources": sources, "total": len(sources)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_knowledge_sources: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/knowledge/documents/{document_id}")
async def get_document_content(request: Request, document_id: str):
    """
    Get full content of a specific document by ID.

    Args:
        document_id: The ID of the document to retrieve

    Returns:
        Document with full content and metadata
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Get the document using encapsulated method
        document_data = retriever.semantic_searcher.get_document_by_id(document_id)

        if not document_data:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        # Extract document data
        metadata = document_data.get("metadata", {})

        # Enforce tenant isolation: if the document has a tenant_id, it must match the current tenant
        try:
            current_tid = getattr(request.state, "tenant_id", None)
            current_tslug = None
            try:
                current_tslug = request.path_params.get("tenant")  # type: ignore[attr-defined]
            except Exception:
                pass

            doc_tid = metadata.get("tenant_id")
            doc_tslug = metadata.get("tenant_slug")

            # Enforce tenant match against id if available; otherwise fall back to slug check
            if current_tid and doc_tid and str(doc_tid) != str(current_tid):
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
            if (not current_tid) and current_tslug and doc_tslug and str(doc_tslug) != str(current_tslug):
                raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        except HTTPException:
            raise
        except Exception:
            # Best-effort; do not fail open/closed on unexpected metadata
            pass
        content = document_data.get("content", "")

        # Count words
        word_count = len(content.split()) if content else 0

        return {
            "id": document_id,
            "source": metadata.get("source", "Unknown"),
            "content": content,
            "content_type": metadata.get("content_type", "unknown"),
            "metadata": metadata,
            "word_count": word_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get document content: {str(e)}")


@router.put("/knowledge/sources/{source_path:path}")
async def update_knowledge_source(request: Request, source_path: str, update_data: SourceUpdateRequest):
    """
    Update metadata for a knowledge source.

    Args:
        source_path: The path of the source to update
        update_data: The data to update (supports manual_content_type, manual_tags)

    Returns:
        Success message and updated source info
    """
    try:
        # Get tenant context for RLS
        tenant_id = getattr(request.state, "tenant_id", None)

        # Get admin user context for audit logging
        from ..core.admin_auth import get_current_admin_user
        from ..core.audit_logger import audit_logger

        admin_user = get_current_admin_user(request)
        username = admin_user.get("username", "unknown") if admin_user else "unknown"
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Track old values for audit logging
        old_values = {}
        new_values = {}

        # Update manual metadata in database if provided
        if update_data.manual_content_type is not None or update_data.manual_tags is not None:
            from sqlalchemy import text

            from ..core.db_session import get_db_session_sync

            with get_db_session_sync() as session:
                if session is None:
                    raise HTTPException(status_code=503, detail="Database not available")

                # Set tenant context for RLS
                if tenant_id:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

                # Check if file exists in database and get current values for audit
                existing = session.execute(
                    text(
                        """
                        SELECT path, manual_content_type, manual_tags,
                               inferred_content_type, inferred_tags
                        FROM knowledge_files
                        WHERE path = :path
                        """
                    ),
                    {"path": source_path},
                ).fetchone()

                if not existing:
                    raise HTTPException(status_code=404, detail=f"Source '{source_path}' not found in database")

                # Capture old values for audit
                old_values = {
                    "manual_content_type": existing[1],
                    "manual_tags": existing[2],
                }

                # Capture new values for audit
                new_values = {
                    "manual_content_type": update_data.manual_content_type,
                    "manual_tags": update_data.manual_tags,
                }

                # Build update query
                updates = []
                params = {"path": source_path}

                if update_data.manual_content_type is not None:
                    updates.append("manual_content_type = :content_type")
                    params["content_type"] = update_data.manual_content_type

                if update_data.manual_tags is not None:
                    updates.append("manual_tags = :tags::jsonb")
                    params["tags"] = update_data.manual_tags

                if updates:
                    updates.extend(
                        [
                            "metadata_provenance = 'manual'",
                            "metadata_updated_at = NOW()",
                            "metadata_version = metadata_version + 1",
                            "status = 'discovered'",  # Mark for reindex
                        ]
                    )

                    query = f"""
                        UPDATE knowledge_files
                        SET {', '.join(updates)}
                        WHERE path = :path
                    """
                    session.execute(text(query), params)
                    logger.info(f"Updated manual metadata for {source_path}")

                    # Check if this is overriding inferred metadata
                    inferred_content_type = existing[3]
                    inferred_tags = existing[4]

                    if update_data.manual_content_type is not None and inferred_content_type:
                        # Log override for content_type
                        audit_logger.log_metadata_override(
                            username=username,
                            file_path=source_path,
                            inferred_value=inferred_content_type,
                            manual_value=update_data.manual_content_type,
                            field_name="content_type",
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                    if update_data.manual_tags is not None and inferred_tags:
                        # Log override for tags
                        audit_logger.log_metadata_override(
                            username=username,
                            file_path=source_path,
                            inferred_value=inferred_tags,
                            manual_value=update_data.manual_tags,
                            field_name="tags",
                            ip_address=ip_address,
                            user_agent=user_agent,
                        )

                    # Log manual update audit event
                    audit_logger.log_metadata_manual_update(
                        username=username,
                        file_path=source_path,
                        old_values=old_values,
                        new_values=new_values,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        success=True,
                    )

                    # Note: Reindex will happen automatically on next sync since we set status='discovered'
                    # The discovery/sync worker will pick up this file and reindex it
                    logger.info(f"Marked {source_path} for reindex by setting status='discovered'")

        # Also update vector store metadata for backward compatibility
        if update_data.content_type is not None:
            # Get the unified retriever from the app state
            if not hasattr(request.app.state, "unified_retriever"):
                raise HTTPException(status_code=503, detail="Knowledge base not initialized")

            retriever = request.app.state.unified_retriever

            # Access the vector store through the semantic_searcher component
            if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
                raise HTTPException(status_code=503, detail="Semantic searcher not available")

            if not retriever.semantic_searcher.vector_store:
                raise HTTPException(status_code=503, detail="Vector store not available")

            # Find all documents from this source using encapsulated method
            documents = retriever.semantic_searcher.get_documents_by_source(source_path)

            if documents:
                # Update metadata for all chunks from this source
                updated_metadatas = []
                document_ids = []
                for doc in documents:
                    doc_id = doc["id"]
                    metadata = doc.get("metadata", {})
                    metadata["content_type"] = update_data.content_type
                    updated_metadatas.append(metadata)
                    document_ids.append(doc_id)

                # Update using encapsulated method
                success = retriever.semantic_searcher.update_documents_metadata(document_ids, updated_metadatas)

                if not success:
                    logger.warning("Failed to update vector store metadata (non-fatal)")

        return {
            "success": True,
            "message": f"Updated metadata for source '{source_path}'",
            "source_path": source_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update knowledge source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update knowledge source: {str(e)}")


@router.delete("/knowledge/sources/{source_path:path}")
async def delete_knowledge_source(request: Request, source_path: str):
    """
    Delete a knowledge source and all its associated chunks.

    Args:
        source_path: The path of the source to delete

    Returns:
        Success message with deletion info
    """
    try:
        # Get the unified retriever from the app state
        if not hasattr(request.app.state, "unified_retriever"):
            raise HTTPException(status_code=503, detail="Knowledge base not initialized")

        retriever = request.app.state.unified_retriever

        # Access the vector store through the semantic_searcher component
        if not hasattr(retriever, "semantic_searcher") or not retriever.semantic_searcher:
            raise HTTPException(status_code=503, detail="Semantic searcher not available")

        if not retriever.semantic_searcher.vector_store:
            raise HTTPException(status_code=503, detail="Vector store not available")

        # Find all documents from this source using encapsulated method
        documents = retriever.semantic_searcher.get_documents_by_source(source_path)

        if not documents:
            raise HTTPException(status_code=404, detail=f"Source '{source_path}' not found")

        chunk_count = len(documents)

        # Delete all chunks from this source using encapsulated method
        success = retriever.semantic_searcher.delete_documents_by_source(source_path)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete source documents")

        # Also try to delete the physical file if it exists in the knowledge directory
        try:
            # Construct the full file path
            knowledge_base_path = os.path.join("backend", "knowledge")
            full_path = os.path.join(knowledge_base_path, source_path)

            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted physical file: {full_path}")
                file_deleted = True
            else:
                logger.info(f"Physical file not found or not in knowledge directory: {full_path}")
                file_deleted = False
        except Exception as e:
            logger.warning(f"Could not delete physical file {source_path}: {e}")
            file_deleted = False

        logger.info(f"Deleted {chunk_count} chunks from source: {source_path}")

        return {
            "success": True,
            "message": f"Deleted source '{source_path}' with {chunk_count} chunks",
            "deleted_chunks": chunk_count,
            "file_deleted": file_deleted,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete knowledge source: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete knowledge source: {str(e)}")


@router.get("/knowledge/files/{file_path:path}/content")
async def get_knowledge_file_content(file_path: str):
    """
    Get the content of a specific knowledge file.

    Args:
        file_path: The path of the file to read

    Returns:
        File content and metadata
    """
    try:
        # Construct the full file path using pathlib for better security
        knowledge_base_path = Path("backend", "knowledge")
        full_path = knowledge_base_path / file_path

        # Security check: ensure the file is within the knowledge directory (resolve symlinks)
        try:
            if (
                knowledge_base_path.resolve() not in full_path.resolve().parents
                and knowledge_base_path.resolve() != full_path.resolve()
            ):
                raise HTTPException(status_code=400, detail="Invalid file path")
        except (OSError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")

        # Read file content
        try:
            with open(full_path, "r", encoding="utf-8") as file:
                content = file.read()
        except UnicodeDecodeError:
            # Try reading as binary and decode with errors
            with open(full_path, "rb") as file:
                raw_content = file.read()
                content = raw_content.decode("utf-8", errors="replace")

        # Get file stats
        file_stats = os.stat(full_path)

        return {
            "content": content,
            "path": file_path,
            "size": file_stats.st_size,
            "modified": file_stats.st_mtime,
            "readable": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read file content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to read file content: {str(e)}")


@router.put("/knowledge/files/{file_path:path}/content")
async def update_knowledge_file_content(file_path: str, request: Request):
    """
    Update the content of a specific knowledge file.

    Args:
        file_path: The path of the file to update
        request: Request containing the new content

    Returns:
        Success message
    """
    try:
        # Parse request body
        body = await request.json()
        new_content = body.get("content", "")

        # Construct the full file path using pathlib for better security
        knowledge_base_path = Path("backend", "knowledge")
        full_path = knowledge_base_path / file_path

        # Security check: ensure the file is within the knowledge directory (resolve symlinks)
        try:
            if (
                knowledge_base_path.resolve() not in full_path.resolve().parents
                and knowledge_base_path.resolve() != full_path.resolve()
            ):
                raise HTTPException(status_code=400, detail="Invalid file path")
        except (OSError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")

        # Create backup of original file
        backup_path = full_path.with_suffix(full_path.suffix + ".backup")
        if full_path.exists():
            shutil.copy2(full_path, backup_path)

        # Write new content
        try:
            with open(full_path, "w", encoding="utf-8") as file:
                file.write(new_content)
        except Exception as write_error:
            # Restore backup if write failed
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, full_path)
            raise write_error
        finally:
            # Remove backup file
            if os.path.exists(backup_path):
                os.remove(backup_path)

        logger.info(f"Updated file content: {file_path}")

        # Trigger re-indexing of the updated file
        try:
            if hasattr(request.app.state, "unified_retriever"):
                retriever = request.app.state.unified_retriever

                # Re-index the updated file using the new reindex_file method
                full_file_path = os.path.join("backend", "knowledge", file_path)
                if os.path.exists(full_file_path):
                    logger.info(f"Re-indexing updated file: {full_file_path}")
                    success = retriever.reindex_file(full_file_path)
                    if success:
                        logger.info(f"Successfully re-indexed: {full_file_path}")
                    else:
                        logger.error(f"Failed to re-index: {full_file_path}")
                else:
                    logger.warning(f"File not found for re-indexing: {full_file_path}")
            else:
                logger.warning("Unified retriever not available for re-indexing")
        except Exception as reindex_error:
            logger.error(f"Failed to re-index file {file_path}: {reindex_error}")
            # Don't fail the save operation if re-indexing fails

        return {
            "success": True,
            "message": f"File '{file_path}' updated successfully",
            "path": file_path,
            "size": len(new_content.encode("utf-8")),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update file content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update file content: {str(e)}")


@router.post("/knowledge/upload")
async def upload_knowledge_files(
    request: Request, files: List[UploadFile] = File(...), session: dict = Depends(require_admin_auth)
):
    """
    Upload multiple files to the knowledge base.
    Supports: MD, PDF, TXT, JSON, HTML, DOCX files.
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Validate file count
        if len(files) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")

        upload_results = []
        successful_uploads = 0

        for file in files:
            try:
                # Validate file size (50MB limit)
                if file.size and file.size > 50 * 1024 * 1024:
                    upload_results.append(
                        {
                            "filename": file.filename,
                            "success": False,
                            "error": f"File too large: {file.size / (1024*1024):.1f}MB (max 50MB)",
                        }
                    )
                    continue

                # Validate file extension
                allowed_extensions = {".md", ".pdf", ".txt", ".json", ".html", ".docx", ".doc"}
                file_ext = Path(file.filename).suffix.lower()
                if file_ext not in allowed_extensions:
                    upload_results.append(
                        {"filename": file.filename, "success": False, "error": f"Unsupported file type: {file_ext}"}
                    )
                    continue

                # Read file content
                file_content = await file.read()
                if not file_content:
                    upload_results.append({"filename": file.filename, "success": False, "error": "Empty file"})
                    continue

                # Create target path in knowledge directory
                knowledge_dir = Path("backend/knowledge")
                knowledge_dir.mkdir(exist_ok=True)

                # Generate unique filename if file already exists
                target_path = knowledge_dir / file.filename
                counter = 1
                while target_path.exists():
                    stem = Path(file.filename).stem
                    suffix = Path(file.filename).suffix
                    target_path = knowledge_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                # Write file
                async with aiofiles.open(target_path, "wb") as f:
                    await f.write(file_content)

                # Reindex the file in the retriever
                reindex_success = False
                try:
                    if hasattr(request.app.state, "unified_retriever") and request.app.state.unified_retriever:
                        retriever = request.app.state.unified_retriever
                        reindex_success = retriever.reindex_file(str(target_path))
                    else:
                        logger.warning("Unified retriever not available for re-indexing")
                except Exception as e:
                    logger.error(f"Failed to reindex uploaded file: {e}")
                    reindex_success = False

                if reindex_success:
                    upload_results.append(
                        {
                            "filename": file.filename,
                            "success": True,
                            "size": len(file_content),
                            "path": str(target_path),
                        }
                    )
                    successful_uploads += 1
                else:
                    upload_results.append(
                        {"filename": file.filename, "success": False, "error": "File saved but indexing failed"}
                    )

            except Exception as e:
                logger.error(f"Failed to process file {file.filename}: {e}")
                upload_results.append({"filename": file.filename, "success": False, "error": str(e)})

        return {
            "success": successful_uploads > 0,
            "message": f"Processed {len(files)} files, {successful_uploads} successful",
            "successful_uploads": successful_uploads,
            "total_files": len(files),
            "results": upload_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/knowledge/metadata/infer")
async def infer_metadata_batch(
    request_body: MetadataInferenceRequest,
    background_tasks: BackgroundTasks,
    tenant_context: dict = Depends(get_tenant_context),
    fastapi_request: Request = None,
) -> dict:
    """
    Trigger batch metadata inference for files.

    Args:
        request_body: Inference request with optional paths, dry_run, and limit
        background_tasks: FastAPI background tasks
        tenant_context: Tenant context from middleware
        fastapi_request: FastAPI request object for audit context

    Returns:
        Status of the inference job
    """
    try:
        from ..core.admin_auth import get_current_admin_user
        from ..core.audit_logger import audit_logger
        from ..core.knowledge_index_db import KnowledgeIndexDB
        from ..core.metadata_inference import infer_metadata_background

        tenant_id = tenant_context.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context not available")

        # Get admin user context for audit logging
        admin_user = get_current_admin_user(fastapi_request) if fastapi_request else None
        username = admin_user.get("username", "unknown") if admin_user else "unknown"
        ip_address = fastapi_request.client.host if fastapi_request and fastapi_request.client else "unknown"
        user_agent = fastapi_request.headers.get("User-Agent", "") if fastapi_request else ""

        db = KnowledgeIndexDB()

        # Determine which files to process
        if request_body.paths:
            # Specific paths provided
            files_to_process = []
            for path in request_body.paths:
                file_metadata = db.get_file_metadata(path, tenant_id=tenant_id)
                if file_metadata:
                    files_to_process.append(file_metadata)
        else:
            # Get all files without manual metadata
            all_files = db.list_files_with_metadata(tenant_id=tenant_id, limit=10000)
            files_to_process = [
                f for f in all_files if f.get("manual_content_type") is None and f.get("manual_tags") in (None, [])
            ]

        # Apply limit if provided
        if request_body.limit:
            files_to_process = files_to_process[: request_body.limit]

        # Log batch inference audit event
        audit_logger.log_metadata_batch_inference(
            username=username,
            file_count=len(files_to_process),
            dry_run=request_body.dry_run,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )

        if request_body.dry_run:
            # Return what would be processed without actually inferring
            return {
                "success": True,
                "dry_run": True,
                "files_to_process": len(files_to_process),
                "files": [
                    {
                        "path": f["path"],
                        "filename": f["filename"],
                        "current_inferred": f.get("inferred_content_type"),
                    }
                    for f in files_to_process
                ],
            }

        # Queue background tasks for inference
        queued_count = 0
        for file_metadata in files_to_process:
            try:
                background_tasks.add_task(
                    infer_metadata_background,
                    file_metadata["path"],
                    tenant_id,
                )
                queued_count += 1
            except Exception as e:
                logger.warning(f"Failed to queue inference for {file_metadata['path']}: {e}")

        logger.info(f"Queued {queued_count} files for metadata inference for tenant {tenant_id}")

        return {
            "success": True,
            "message": f"Queued {queued_count} files for metadata inference",
            "queued_count": queued_count,
            "total_eligible": len(files_to_process),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger metadata inference: {e}")
        # Log failed audit event
        if fastapi_request:
            from ..core.admin_auth import get_current_admin_user
            from ..core.audit_logger import audit_logger

            admin_user = get_current_admin_user(fastapi_request)
            username = admin_user.get("username", "unknown") if admin_user else "unknown"
            ip_address = fastapi_request.client.host if fastapi_request.client else "unknown"
            user_agent = fastapi_request.headers.get("User-Agent", "")

            audit_logger.log_metadata_batch_inference(
                username=username,
                file_count=0,
                dry_run=request_body.dry_run,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message=str(e),
            )
        raise HTTPException(status_code=500, detail="Failed to trigger metadata inference")


@router.get("/knowledge/metadata/metrics")
async def get_metadata_metrics(
    request: Request,
    tenant_context: dict = Depends(get_tenant_context),
) -> dict:
    """
    Get metadata inference and management metrics.

    Returns aggregated statistics about:
    - Inference coverage (% of files with metadata)
    - Inference accuracy (override rate)
    - Confidence distribution
    - User activity

    Args:
        request: FastAPI request object
        tenant_context: Tenant context from middleware

    Returns:
        Dictionary with metadata metrics
    """
    try:
        from sqlalchemy import text

        from ..core.db_session import get_db_session_sync

        tenant_id = tenant_context.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context not available")

        with get_db_session_sync() as session:
            if session is None:
                raise HTTPException(status_code=503, detail="Database not available")

            # Set tenant context for RLS
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})

            # Get total files and files with metadata
            coverage_stats = session.execute(
                text(
                    """
                    SELECT
                        COUNT(*) as total_files,
                        COUNT(inferred_content_type) as files_with_inferred,
                        COUNT(manual_content_type) as files_with_manual,
                        COUNT(CASE WHEN manual_content_type IS NOT NULL OR inferred_content_type IS NOT NULL THEN 1 END) as files_with_any_metadata
                    FROM knowledge_files
                    WHERE tenant_id = :tenant_id
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchone()

            # Get override statistics (manual overwrites inferred)
            override_stats = session.execute(
                text(
                    """
                    SELECT
                        COUNT(*) as total_overrides
                    FROM knowledge_files
                    WHERE tenant_id = :tenant_id
                      AND manual_content_type IS NOT NULL
                      AND inferred_content_type IS NOT NULL
                      AND manual_content_type != inferred_content_type
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchone()

            # Get confidence distribution
            confidence_stats = session.execute(
                text(
                    """
                    SELECT
                        AVG(inferred_confidence) as avg_confidence,
                        MIN(inferred_confidence) as min_confidence,
                        MAX(inferred_confidence) as max_confidence,
                        COUNT(CASE WHEN inferred_confidence >= 0.8 THEN 1 END) as high_confidence_count,
                        COUNT(CASE WHEN inferred_confidence >= 0.5 AND inferred_confidence < 0.8 THEN 1 END) as medium_confidence_count,
                        COUNT(CASE WHEN inferred_confidence < 0.5 THEN 1 END) as low_confidence_count
                    FROM knowledge_files
                    WHERE tenant_id = :tenant_id
                      AND inferred_confidence IS NOT NULL
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchone()

            # Get content type distribution
            content_type_dist = session.execute(
                text(
                    """
                    SELECT
                        COALESCE(manual_content_type, inferred_content_type) as content_type,
                        COUNT(*) as count
                    FROM knowledge_files
                    WHERE tenant_id = :tenant_id
                      AND (manual_content_type IS NOT NULL OR inferred_content_type IS NOT NULL)
                    GROUP BY COALESCE(manual_content_type, inferred_content_type)
                    ORDER BY count DESC
                    LIMIT 10
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchall()

            # Get recent audit activity from security_events
            recent_activity = session.execute(
                text(
                    """
                    SELECT
                        event_type,
                        COUNT(*) as count,
                        COUNT(DISTINCT identifier) as unique_users
                    FROM security_events
                    WHERE tenant_id = :tenant_id
                      AND event_type LIKE 'audit_metadata_%'
                      AND created_at >= NOW() - INTERVAL '7 days'
                    GROUP BY event_type
                    ORDER BY count DESC
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchall()

            # Calculate metrics
            total_files = coverage_stats[0] or 0
            files_with_inferred = coverage_stats[1] or 0
            files_with_manual = coverage_stats[2] or 0
            files_with_any_metadata = coverage_stats[3] or 0

            coverage_percentage = (files_with_any_metadata / total_files * 100) if total_files > 0 else 0
            override_count = override_stats[0] or 0
            override_rate = (override_count / files_with_inferred * 100) if files_with_inferred > 0 else 0

            avg_confidence = float(confidence_stats[0]) if confidence_stats[0] else 0.0
            min_confidence = float(confidence_stats[1]) if confidence_stats[1] else 0.0
            max_confidence = float(confidence_stats[2]) if confidence_stats[2] else 0.0

            return {
                "coverage": {
                    "total_files": total_files,
                    "files_with_metadata": files_with_any_metadata,
                    "files_with_inferred": files_with_inferred,
                    "files_with_manual": files_with_manual,
                    "coverage_percentage": round(coverage_percentage, 2),
                },
                "inference_accuracy": {
                    "total_inferred": files_with_inferred,
                    "manual_overrides": override_count,
                    "override_rate_percentage": round(override_rate, 2),
                },
                "confidence_distribution": {
                    "average": round(avg_confidence, 3),
                    "min": round(min_confidence, 3),
                    "max": round(max_confidence, 3),
                    "high_confidence_count": confidence_stats[4] or 0,
                    "medium_confidence_count": confidence_stats[5] or 0,
                    "low_confidence_count": confidence_stats[6] or 0,
                },
                "content_type_distribution": [{"content_type": row[0], "count": row[1]} for row in content_type_dist],
                "recent_activity": [
                    {"event_type": row[0].replace("audit_", ""), "count": row[1], "unique_users": row[2]}
                    for row in recent_activity
                ],
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metadata metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metadata metrics")
