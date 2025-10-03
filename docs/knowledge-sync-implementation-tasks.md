# Knowledge Sync & Admin Consistency — Implementation Tasks

This task list tracks the end-to-end delivery of the knowledge sync feature.

## Phase 1 — Backend Foundations

- [ ] Add KnowledgeIndexDB (SQLite) under `backend/core/knowledge_index_db.py`
  - [ ] Schema: `knowledge_files` with fields (path, size, mtime, hash, status, chunk_count, vector_count, timestamps, last_error)
  - [ ] Methods: `init`, `upsert_file`, `update_indexed`, `record_error`, `update_vector_count`, `get_by_path`, `list_files(filter)`
  - [ ] Use `get_database_path('knowledge_index.db')`

- [ ] Add KnowledgeStateSync service under `backend/core/knowledge_state_sync.py`
  - [ ] `scan_filesystem(dirs)` — enumerate candidates (reuse ContentIndexer.should_index_file), capture size/mtime
  - [ ] `scan_vector_store()` — aggregate docs by `metadata.source`
  - [ ] `read_hash_tracking()` — load `index_metadata.json` from `persist_dir`
  - [ ] `diff()` — compute discovered_not_indexed, changed_files, vector_orphans, tracked_but_missing
  - [ ] `reconcile(dry_run, allow_deletes, paths)` — reindex, delete-orphans, update DB
  - [ ] `summary()` — counts for UI

- [ ] Wire DB updates into `UnifiedRetriever.reindex_file` (on success)

- [ ] Admin API routes (new): `backend/routes/knowledge_admin_sync.py`
  - [ ] GET `/api/admin/knowledge/consistency` — return diff summary (with samples) and counts
  - [ ] POST `/api/admin/knowledge/reconcile` — execute reconcile with flags; return report
  - [ ] GET `/api/admin/knowledge/files` — enriched DB-backed file list; filter by status
  - [ ] POST `/api/admin/knowledge/reindex-file` — targeted file reindex
  - [ ] Add router in `app_factory.py`

- [ ] Startup integration
  - [ ] Instantiate state sync in `app_initializer_v2.initialize_app_state`
  - [ ] Run `validate_and_reconcile(dry_run=True)` after vector store init; log summary
  - [ ] Optional: add `KNOWLEDGE_SYNC_INTERVAL_SECONDS` loop (off by default)

## Phase 2 — Admin Frontend

- [ ] Add Consistency view
  - [ ] Summary cards + tables for mismatches
  - [ ] Reconcile panel (dry-run, allow-deletes, paths)
  - [ ] API wiring to new endpoints

- [ ] Enhance Sources view to consume enriched `/knowledge/files`
  - [ ] Show `status`, `chunk_count`, `vector_count`
  - [ ] Actions: Reindex, Delete from index (allow-deletes)

## Phase 3 — Migration & Hardening

- [ ] Initial DB backfill: scan FS and vector store; import `index_metadata.json` hashes where matching
- [ ] Add simple tests for diff builder and reconcile planner (mock FS/vector)
- [ ] Tune logging & error handling; ensure low-risk defaults (dry run, no deletes)

## Phase 4 — Polish

- [ ] Persist classification data to DB (optional)
- [ ] Periodic background sync toggles per environment
- [ ] Health endpoint `/api/admin/knowledge/health`

