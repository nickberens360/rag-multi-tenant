"""
Knowledge Index metadata database (Postgres).

Tracks file discovery and indexing status to enable robust reconciliation
between the filesystem, vector database, and legacy hash tracking.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from .db_session import get_db_session_sync

logger = logging.getLogger(__name__)


class KnowledgeIndexDB:
    """Postgres-backed wrapper for knowledge index metadata."""

    def __init__(self) -> None:
        # Schema ensured by Alembic migrations
        pass

    @staticmethod
    def _split_path(path: str) -> Dict[str, Any]:
        p = Path(path)
        return {
            "dir": str(p.parent),
            "filename": p.name,
            "ext": p.suffix.lower().lstrip("."),
        }

    def upsert_file(
        self,
        path: str,
        *,
        size: Optional[int] = None,
        mtime: Optional[float] = None,
        file_hash: Optional[str] = None,
        tenant_id: Optional[str] = None,
        scope: str = "shared",
    ) -> None:
        parts = self._split_path(path)
        with get_db_session_sync() as session:
            if session is None:
                return
            # Ensure tenant GUC is set for RLS when a tenant-scoped write is requested
            try:
                if tenant_id:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            except Exception:
                pass
            session.execute(
                text(
                    """
                    INSERT INTO knowledge_files(path, dir, filename, ext, size, mtime, hash, status, tenant_id, scope)
                    VALUES (:path, :dir, :filename, :ext, :size, :mtime, :hash,
                            COALESCE((SELECT status FROM knowledge_files WHERE path = :path AND
                                     tenant_id = COALESCE(:tenant_id, CAST(current_setting('app.default_tenant_id', true) AS uuid))), 'discovered'),
                            :tenant_id, :scope)
                    ON CONFLICT (tenant_id, path) DO UPDATE SET
                        dir=EXCLUDED.dir,
                        filename=EXCLUDED.filename,
                        ext=EXCLUDED.ext,
                        size=COALESCE(EXCLUDED.size, knowledge_files.size),
                        mtime=COALESCE(EXCLUDED.mtime, knowledge_files.mtime),
                        hash=COALESCE(EXCLUDED.hash, knowledge_files.hash),
                        scope=EXCLUDED.scope
                    """
                ),
                {
                    "path": path,
                    "dir": parts["dir"],
                    "filename": parts["filename"],
                    "ext": parts["ext"],
                    "size": size,
                    "mtime": mtime,
                    "hash": file_hash,
                    "tenant_id": tenant_id,
                    "scope": scope,
                },
            )

    def update_indexed(
        self,
        path: str,
        *,
        file_hash: Optional[str],
        chunk_count: Optional[int],
        vector_count: Optional[int],
        tenant_id: Optional[str] = None,
    ) -> None:
        with get_db_session_sync() as session:
            if session is None:
                return
            try:
                if tenant_id:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            except Exception:
                pass
            session.execute(
                text(
                    """
                    UPDATE knowledge_files
                    SET status='indexed', hash=COALESCE(:hash, hash),
                        chunk_count=COALESCE(:chunk_count, chunk_count),
                        vector_count=COALESCE(:vector_count, vector_count),
                        indexed_at=now(),
                        last_error=NULL, last_error_at=NULL
                    WHERE path=:path AND tenant_id = COALESCE(:tenant_id, CAST(current_setting('app.default_tenant_id', true) AS uuid))
                    """
                ),
                {
                    "path": path,
                    "hash": file_hash,
                    "chunk_count": chunk_count,
                    "vector_count": vector_count,
                    "tenant_id": tenant_id,
                },
            )

    def update_vector_count(self, path: str, *, vector_count: int, tenant_id: Optional[str] = None) -> None:
        with get_db_session_sync() as session:
            if session is not None:
                try:
                    if tenant_id:
                        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
                except Exception:
                    pass
                session.execute(
                    text(
                        "UPDATE knowledge_files SET vector_count=:vc WHERE path=:path AND tenant_id = COALESCE(:tenant_id, CAST(current_setting('app.default_tenant_id', true) AS uuid))"
                    ),
                    {"vc": vector_count, "path": path, "tenant_id": tenant_id},
                )

    def update_status(self, path: str, *, status: str, tenant_id: Optional[str] = None) -> None:
        with get_db_session_sync() as session:
            if session is not None:
                try:
                    if tenant_id:
                        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
                except Exception:
                    pass
                session.execute(
                    text(
                        "UPDATE knowledge_files SET status=:st WHERE path=:path AND tenant_id = COALESCE(:tenant_id, CAST(current_setting('app.default_tenant_id', true) AS uuid))"
                    ),
                    {"st": status, "path": path, "tenant_id": tenant_id},
                )

    def record_error(self, path: str, *, error: str, tenant_id: Optional[str] = None) -> None:
        with get_db_session_sync() as session:
            if session is not None:
                try:
                    if tenant_id:
                        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
                except Exception:
                    pass
                session.execute(
                    text(
                        """
                        UPDATE knowledge_files
                        SET status='error', last_error=:err, last_error_at=now()
                        WHERE path=:path AND tenant_id = COALESCE(:tenant_id, CAST(current_setting('app.default_tenant_id', true) AS uuid))
                        """
                    ),
                    {"err": error[:1000], "path": path, "tenant_id": tenant_id},
                )

    def get_by_path(self, path: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with get_db_session_sync() as session:
            if session is None:
                return None
            try:
                if tenant_id:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            except Exception:
                pass
            row = session.execute(
                text(
                    "SELECT id, path, dir, filename, ext, size, mtime, hash, status, chunk_count, vector_count, discovered_at, indexed_at, last_error, last_error_at, tenant_id, scope FROM knowledge_files WHERE path = :path AND tenant_id = COALESCE(:tenant_id, CAST(current_setting('app.default_tenant_id', true) AS uuid))"
                ),
                {"path": path, "tenant_id": tenant_id},
            ).first()
            if not row:
                return None
            cols = [
                "id",
                "path",
                "dir",
                "filename",
                "ext",
                "size",
                "mtime",
                "hash",
                "status",
                "chunk_count",
                "vector_count",
                "discovered_at",
                "indexed_at",
                "last_error",
                "last_error_at",
                "tenant_id",
                "scope",
            ]
            return {c: row[i] for i, c in enumerate(cols)}

    def list_files(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List files from the knowledge index.

        SECURITY: When tenant_id is provided, ONLY returns files belonging to that tenant.
        The include_shared parameter has been removed to prevent cross-tenant data leakage.
        """
        with get_db_session_sync() as session:
            if session is None:
                return []

            # Ensure tenant context for RLS (reads) when provided
            try:
                if tenant_id:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            except Exception:
                pass

            # Build WHERE clause for tenant filtering
            where_conditions = []
            params = {"lim": int(limit), "off": int(offset)}

            # SECURITY: ONLY include tenant-specific files when tenant_id is provided
            if tenant_id:
                where_conditions.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id

            if status:
                where_conditions.append("status = :st")
                params["st"] = status

            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            query = text(
                f"""
                SELECT id, path, dir, filename, ext, size, mtime, hash, status, chunk_count, vector_count,
                       discovered_at, indexed_at, last_error, last_error_at, tenant_id, scope
                FROM knowledge_files{where_clause} ORDER BY filename LIMIT :lim OFFSET :off
            """
            )

            rows = session.execute(query, params).fetchall()
            cols = [
                "id",
                "path",
                "dir",
                "filename",
                "ext",
                "size",
                "mtime",
                "hash",
                "status",
                "chunk_count",
                "vector_count",
                "discovered_at",
                "indexed_at",
                "last_error",
                "last_error_at",
                "tenant_id",
                "scope",
            ]
            return [{c: r[i] for i, c in enumerate(cols)} for r in rows]

    def get_file_metadata(self, path: str, tenant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get file metadata including effective (manual > inferred) metadata fields.

        Returns:
            Dictionary with file info plus effective_content_type, effective_tags, and provenance
        """
        with get_db_session_sync() as session:
            if session is None:
                return None

            try:
                if tenant_id:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            except Exception:
                pass

            row = session.execute(
                text(
                    """
                    SELECT id, path, dir, filename, ext, size, mtime, hash, status,
                           chunk_count, vector_count, discovered_at, indexed_at,
                           last_error, last_error_at, tenant_id, scope,
                           manual_content_type, manual_tags, inferred_content_type,
                           inferred_tags, inferred_confidence, metadata_provenance,
                           metadata_updated_by, metadata_updated_at, metadata_version,
                           COALESCE(manual_content_type, inferred_content_type) as effective_content_type,
                           COALESCE(manual_tags, inferred_tags, '[]'::jsonb) as effective_tags
                    FROM knowledge_files
                    WHERE path = :path
                      AND tenant_id = COALESCE(:tenant_id, CAST(current_setting('app.default_tenant_id', true) AS uuid))
                    """
                ),
                {"path": path, "tenant_id": tenant_id},
            ).first()

            if not row:
                return None

            cols = [
                "id",
                "path",
                "dir",
                "filename",
                "ext",
                "size",
                "mtime",
                "hash",
                "status",
                "chunk_count",
                "vector_count",
                "discovered_at",
                "indexed_at",
                "last_error",
                "last_error_at",
                "tenant_id",
                "scope",
                "manual_content_type",
                "manual_tags",
                "inferred_content_type",
                "inferred_tags",
                "inferred_confidence",
                "metadata_provenance",
                "metadata_updated_by",
                "metadata_updated_at",
                "metadata_version",
                "effective_content_type",
                "effective_tags",
            ]
            return {c: row[i] for i, c in enumerate(cols)}

    def list_files_with_metadata(
        self,
        *,
        status: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List files with metadata including effective fields.

        SECURITY: When tenant_id is provided, ONLY returns files belonging to that tenant.
        """
        with get_db_session_sync() as session:
            if session is None:
                return []

            try:
                if tenant_id:
                    session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            except Exception:
                pass

            # Build WHERE clause for tenant filtering
            where_conditions = []
            params = {"lim": int(limit), "off": int(offset)}

            if tenant_id:
                where_conditions.append("tenant_id = :tenant_id")
                params["tenant_id"] = tenant_id

            if status:
                where_conditions.append("status = :st")
                params["st"] = status

            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            query = text(
                f"""
                SELECT id, path, dir, filename, ext, size, mtime, hash, status,
                       chunk_count, vector_count, discovered_at, indexed_at,
                       last_error, last_error_at, tenant_id, scope,
                       manual_content_type, manual_tags, inferred_content_type,
                       inferred_tags, inferred_confidence, metadata_provenance,
                       metadata_updated_by, metadata_updated_at, metadata_version,
                       COALESCE(manual_content_type, inferred_content_type) as effective_content_type,
                       COALESCE(manual_tags, inferred_tags, '[]'::jsonb) as effective_tags
                FROM knowledge_files{where_clause}
                ORDER BY filename
                LIMIT :lim OFFSET :off
                """
            )

            rows = session.execute(query, params).fetchall()
            cols = [
                "id",
                "path",
                "dir",
                "filename",
                "ext",
                "size",
                "mtime",
                "hash",
                "status",
                "chunk_count",
                "vector_count",
                "discovered_at",
                "indexed_at",
                "last_error",
                "last_error_at",
                "tenant_id",
                "scope",
                "manual_content_type",
                "manual_tags",
                "inferred_content_type",
                "inferred_tags",
                "inferred_confidence",
                "metadata_provenance",
                "metadata_updated_by",
                "metadata_updated_at",
                "metadata_version",
                "effective_content_type",
                "effective_tags",
            ]
            return [{c: r[i] for i, c in enumerate(cols)} for r in rows]
