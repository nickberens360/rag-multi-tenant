"""
Knowledge state synchronization service.

Compares filesystem, vector store, and legacy hash tracking to detect drift
and optionally reconcile by re-indexing files and cleaning up orphans.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .knowledge_index_db import KnowledgeIndexDB

logger = logging.getLogger(__name__)


@dataclass
class ConsistencySummary:
    filesystem_files: int
    vector_docs: int
    tracked_files: int
    discovered_not_indexed: int
    changed_files: int
    vector_orphans: int
    tracked_but_missing: int


class KnowledgeStateSync:
    def __init__(self, unified_retriever: Any, *, persist_dir: str, index_dirs: List[str]) -> None:
        self.unified_retriever = unified_retriever
        self.persist_dir = persist_dir
        self.index_dirs = index_dirs
        self.db = KnowledgeIndexDB()

    @staticmethod
    def _extract_tenant_slug_from_path(path_str: str) -> Optional[str]:
        try:
            parts = path_str.replace("\\", "/").split("/")
            for i, p in enumerate(parts):
                if p == "tenants" and i + 1 < len(parts):
                    slug = parts[i + 1]
                    if slug and slug not in {"shared", "documents"}:
                        return slug
            return None
        except Exception:
            return None

    # -------------------- Scanners --------------------
    def scan_filesystem(
        self, tenant_id: Optional[str] = None, tenant_slug: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        files: Dict[str, Dict[str, Any]] = {}
        for directory in self.index_dirs:
            base = Path(directory)
            if not base.exists():
                continue

            # Determine scope and tenant info based on path
            for p in base.rglob("*"):
                if p.is_file() and not p.name.startswith("."):
                    try:
                        stat = p.stat()
                        # Always include in FS map; tenant filtering is applied at response stage
                        files[str(p)] = {"size": stat.st_size, "mtime": stat.st_mtime, "ext": p.suffix.lower()}

                        # Determine scope based on path
                        path_str = str(p)
                        # Extract slug from path; if provided tenant_slug doesn't match, skip
                        extracted_slug = self._extract_tenant_slug_from_path(path_str)

                        # For DB upsert scoping, only proceed when slug matches (if provided)
                        if tenant_slug is not None and extracted_slug != tenant_slug:
                            # Skip DB write for other tenants
                            continue

                        # Best-effort derive tenant_id for DB upsert; safe to skip if unresolved
                        actual_tenant_id = tenant_id
                        if actual_tenant_id is None and extracted_slug is not None:
                            try:
                                from sqlalchemy import text

                                from .db_session import get_db_session_sync as _get

                                with _get() as session:
                                    if session is not None:
                                        row = session.execute(
                                            text("SELECT id FROM tenants WHERE slug = :slug AND deleted_at IS NULL"),
                                            {"slug": extracted_slug},
                                        ).first()
                                        if row and row[0]:
                                            actual_tenant_id = str(row[0])
                            except Exception:
                                actual_tenant_id = None

                        # Opportunistic DB upsert for discovery with tenant info (only if we have a tenant_id)
                        if actual_tenant_id is not None:
                            self.db.upsert_file(
                                str(p),
                                size=stat.st_size,
                                mtime=stat.st_mtime,
                                tenant_id=actual_tenant_id,
                                scope="tenant",
                            )
                    except OSError:
                        continue
        return files

    def scan_vector_store(
        self, max_docs: int = 100_000, page_size: int = 10_000, tenant_id: Optional[str] = None
    ) -> Tuple[int, Dict[str, int]]:
        """Return total vector docs and counts grouped by metadata.source, optionally filtered by tenant."""
        searcher = getattr(self.unified_retriever, "semantic_searcher", None)
        if not searcher or not searcher.vector_store:
            return 0, {}

        collection = searcher.vector_store._collection
        try:
            # SECURITY: If tenant filtering is requested, use tenant-aware count (tenant-only, NO shared)
            if tenant_id and hasattr(searcher, "get_count_for_tenant"):
                total = searcher.get_count_for_tenant(tenant_id)
            else:
                total = collection.count()
        except Exception:
            total = 0

        if total == 0:
            return 0, {}

        counts: Dict[str, int] = defaultdict(int)
        fetched = 0
        offset = 0
        to_fetch = min(total, max_docs)

        while fetched < to_fetch:
            limit = min(page_size, to_fetch - fetched)
            try:
                # Apply tenant filtering if requested
                where_filter = None
                if tenant_id:
                    # Tenant-only scan
                    where_filter = {"tenant_id": tenant_id}

                res = collection.get(include=["metadatas"], limit=limit, offset=offset, where=where_filter)
                metadatas = res.get("metadatas", []) if isinstance(res, dict) else []
                if not metadatas:
                    break
                for md in metadatas:
                    src = None
                    try:
                        src = md.get("source") if isinstance(md, dict) else None
                    except Exception:
                        src = None
                    if src:
                        counts[src] += 1
                n = len(metadatas)
                fetched += n
                offset += n
                if n == 0:
                    break
            except Exception as e:
                logger.warning(f"Vector scan halted at offset {offset}: {e}")
                break

        # Update DB vector_count snapshots with tenant context
        for path, vc in counts.items():
            try:
                # Extract tenant from path or use provided tenant_id
                path_tenant_id = None
                if "/tenants/" in path and tenant_id:
                    path_tenant_id = tenant_id
                self.db.update_vector_count(path, vector_count=vc, tenant_id=path_tenant_id)
            except Exception:
                pass

        return total, dict(counts)

    def read_hash_tracking(self) -> Dict[str, Any]:
        try:
            meta_path = Path(self.persist_dir) / "index_metadata.json"
            if not meta_path.exists():
                return {}
            with meta_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to read index_metadata.json: {e}")
            return {}

    # -------------------- Diff & Reconcile --------------------
    def build_diff(
        self,
        *,
        fs: Dict[str, Dict[str, Any]],
        vcounts: Dict[str, int],
        tracked: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        fs_paths = set(fs.keys())
        vec_paths = set(vcounts.keys())
        tracked_paths = set(tracked.keys())

        discovered_not_indexed: List[str] = []
        changed_files: List[str] = []
        vector_orphans: List[str] = []
        tracked_but_missing: List[str] = []

        # Discovered but not indexed (FS exists, vector_count==0)
        for p in fs_paths:
            if vcounts.get(p, 0) == 0:
                discovered_not_indexed.append(p)

        # Changed files — compare mtime/hash vs DB/legacy when available
        for p in fs_paths & (vec_paths | tracked_paths):
            db_row = self.db.get_by_path(p, tenant_id=tenant_id)
            fs_mtime = fs[p].get("mtime")
            fs_size = fs[p].get("size")
            # Heuristic: if DB has older mtime/size or legacy hash mismatches, mark as changed
            legacy_entry = tracked.get(p)
            legacy_hash = legacy_entry if isinstance(legacy_entry, str) else (legacy_entry or {}).get("hash")
            if db_row:
                db_mtime = db_row.get("mtime")
                db_size = db_row.get("size")
                if (db_mtime and fs_mtime and fs_mtime > db_mtime + 1) or (db_size and fs_size and fs_size != db_size):
                    changed_files.append(p)
            else:
                # No DB row yet, but present in vector/tracked; conservatively treat as changed
                changed_files.append(p)
            # If no vector docs but tracked hash exists, also mark
            if vcounts.get(p, 0) == 0 and legacy_hash:
                if p not in changed_files:
                    changed_files.append(p)

        # Vector orphans (in vector store but file missing on disk)
        for p in vec_paths - fs_paths:
            vector_orphans.append(p)

        # Tracked but missing (in legacy metadata but file missing on disk)
        for p in tracked_paths - fs_paths:
            tracked_but_missing.append(p)

        return {
            "discovered_not_indexed": sorted(discovered_not_indexed),
            "changed_files": sorted(set(changed_files)),
            "vector_orphans": sorted(vector_orphans),
            "tracked_but_missing": sorted(tracked_but_missing),
        }

    def summarize(
        self, diff: Dict[str, List[str]], *, fs_count: int, vec_total: int, tracked_count: int
    ) -> ConsistencySummary:
        return ConsistencySummary(
            filesystem_files=fs_count,
            vector_docs=vec_total,
            tracked_files=tracked_count,
            discovered_not_indexed=len(diff.get("discovered_not_indexed", [])),
            changed_files=len(diff.get("changed_files", [])),
            vector_orphans=len(diff.get("vector_orphans", [])),
            tracked_but_missing=len(diff.get("tracked_but_missing", [])),
        )

    def validate(
        self, tenant_id: Optional[str] = None, tenant_slug: Optional[str] = None
    ) -> Tuple[ConsistencySummary, Dict[str, List[str]]]:
        fs = self.scan_filesystem(tenant_id=tenant_id, tenant_slug=tenant_slug)
        vec_total, vcounts = self.scan_vector_store(tenant_id=tenant_id)
        tracked = self.read_hash_tracking()

        # Filter filesystem and tracked data by tenant for accurate summary stats
        fs_filtered = fs
        tracked_filtered = tracked
        if tenant_slug:
            marker = f"tenants/{tenant_slug}/"
            default_slug = os.getenv("DEFAULT_TENANT_SLUG", "default")
            if tenant_slug == default_slug:
                # Default tenant: include files that don't have "tenants/" OR have "tenants/default/"
                fs_filtered = {p: v for p, v in fs.items() if ("tenants/" not in p) or (marker in p)}
                tracked_filtered = {p: v for p, v in tracked.items() if ("tenants/" not in p) or (marker in p)}
            else:
                # Non-default tenant: only include files with "tenants/{slug}/"
                fs_filtered = {p: v for p, v in fs.items() if marker in p}
                tracked_filtered = {p: v for p, v in tracked.items() if marker in p}

        # Use filtered data for diff calculation to ensure tenant isolation in mismatch detection
        diff = self.build_diff(fs=fs_filtered, vcounts=vcounts, tracked=tracked_filtered, tenant_id=tenant_id)
        summary = self.summarize(
            diff, fs_count=len(fs_filtered), vec_total=vec_total, tracked_count=len(tracked_filtered)
        )
        return summary, diff

    def reconcile(
        self,
        *,
        dry_run: bool = True,
        allow_deletes: bool = False,
        paths: Optional[List[str]] = None,
        limit: Optional[int] = None,
        tenant_id: Optional[str] = None,
        tenant_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        summary, diff = self.validate(tenant_id=tenant_id, tenant_slug=tenant_slug)
        actions: Dict[str, List[str]] = {
            "reindexed": [],
            "deleted_orphans": [],
            "errors": [],
        }

        # Helper to filter selected paths
        def _select(items: Iterable[str]) -> List[str]:
            selected = list(items)
            if paths:
                selected = [p for p in selected if p in paths]
            if limit is not None:
                selected = selected[: max(0, int(limit))]
            return selected

        # Reindex candidates
        to_reindex = _select(diff.get("changed_files", []) + diff.get("discovered_not_indexed", []))

        if dry_run:
            return {
                "summary": summary.__dict__,
                "diff": diff,
                "planned": {"reindex": to_reindex, "delete_orphans": _select(diff.get("vector_orphans", []))},
            }

        # Execute reindex
        for p in to_reindex:
            try:
                ok = self.unified_retriever.reindex_file(p)
                if ok:
                    # After reindex, best-effort update DB; chunk_count unknown here
                    try:
                        # Compute hash via indexer for accuracy
                        file_hash = self.unified_retriever.content_indexer.compute_file_hash(Path(p))
                    except Exception:
                        file_hash = None
                    # Determine tenant_id from path if not provided
                    path_tenant_id = None
                    if "/tenants/" in p and tenant_id:
                        path_tenant_id = tenant_id
                    self.db.update_indexed(
                        p, file_hash=file_hash, chunk_count=None, vector_count=None, tenant_id=path_tenant_id
                    )
                    actions["reindexed"].append(p)
                else:
                    path_tenant_id = None
                    if "/tenants/" in p and tenant_id:
                        path_tenant_id = tenant_id
                    self.db.record_error(p, error="Reindex failed", tenant_id=path_tenant_id)
                    actions["errors"].append(p)
            except Exception as e:
                logger.error(f"Failed to reindex {p}: {e}")
                path_tenant_id = None
                if "/tenants/" in p and tenant_id:
                    path_tenant_id = tenant_id
                self.db.record_error(p, error=str(e), tenant_id=path_tenant_id)
                actions["errors"].append(p)

        # Delete orphans if allowed
        if allow_deletes:
            searcher = getattr(self.unified_retriever, "semantic_searcher", None)
            if searcher and searcher.vector_store:
                for p in _select(diff.get("vector_orphans", [])):
                    try:
                        ok = searcher.delete_documents_by_source(p)
                        if ok:
                            path_tenant_id = None
                            if "/tenants/" in p and tenant_id:
                                path_tenant_id = tenant_id
                            self.db.update_status(p, status="missing_file", tenant_id=path_tenant_id)
                            actions["deleted_orphans"].append(p)
                        else:
                            actions["errors"].append(p)
                    except Exception as e:
                        logger.error(f"Failed to delete orphan {p}: {e}")
                        actions["errors"].append(p)

        # Record last reconcile time when we actually performed actions
        try:
            if not dry_run:
                from datetime import datetime

                marker = Path(self.persist_dir) / ".last_reconcile"
                marker.write_text(datetime.now().isoformat(), encoding="utf-8")
        except Exception:
            pass

        return {"summary": summary.__dict__, "diff": diff, "actions": actions}
