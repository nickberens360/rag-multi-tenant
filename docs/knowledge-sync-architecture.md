# Knowledge Sync & Consistency Architecture (Draft)

This document proposes a robust architecture to keep the knowledge base consistent across three data layers:

- File System: authoritative source of documents (e.g., `backend/knowledge`, `public/`)
- Vector Database: ChromaDB persistent collection with document chunks and metadata
- Hash Tracking: existing `index_metadata.json` under `persist_dir` (legacy cache)

Goals:
- Automatic detection and reconciliation of mismatches
- Persistent file-level metadata for auditing and incremental sync
- Admin visibility and targeted repair actions

## Components

- KnowledgeIndexDB (SQLite)
  - File-level metadata: path, size, mtime, hash, status, chunk_count, timestamps, last_error
  - Status lifecycle: discovered → pending_index → indexed | error; orphaned | missing_file for drift
  - Location: `backend/logs/knowledge_index.db` (or `/data` in production via `get_database_path`)

- KnowledgeStateSync (service)
  - Scans all three layers and computes a diff
  - Reconciles deltas: reindex missing/changed files; optionally delete vector orphans
  - Provides a dry-run mode and detailed summaries for admin

- Admin APIs
  - `GET /api/admin/knowledge/consistency`: current mismatches summary + samples
  - `POST /api/admin/knowledge/reconcile`: dry run or execute, optional path filters
  - `GET /api/admin/knowledge/files`: enriched file list with status + counts
  - `POST /api/admin/knowledge/reindex-file`: targeted reindex

## Data Model (SQLite)

Table `knowledge_files`:
- id INTEGER PK
- path TEXT UNIQUE NOT NULL
- dir TEXT
- filename TEXT
- ext TEXT
- size INTEGER
- mtime REAL
- hash TEXT
- status TEXT CHECK(status IN ('discovered','pending_index','indexed','error','orphaned','missing_file')) NOT NULL DEFAULT 'discovered'
- chunk_count INTEGER DEFAULT 0
- vector_count INTEGER DEFAULT 0
- discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- indexed_at TIMESTAMP
- last_error TEXT
- last_error_at TIMESTAMP

Rationale:
- `vector_count` helps detect orphans/missing index without loading all docs.
- `mtime` and `size` provide cheap change detection. `hash` used when needed.

## Sync Algorithm (High Level)

Inputs:
- Filesystem scan: enumerate candidate files; read `size`, `mtime` (and `hash` lazily)
- Vector store scan: group docs by `metadata.source`, count chunks per source
- Hash tracking: load `index_metadata.json` (legacy)

Diff:
- discovered_not_indexed: on FS, `vector_count==0` and `status!=indexed`
- changed_files: on FS, hash/mtime differs from DB/legacy OR `vector_count` < expected
- vector_orphans: in vector store but file missing on FS
- tracked_but_missing: in legacy `index_metadata.json` but missing on FS

Reconcile (configurable):
- Reindex changed/missing-in-vector files (via `UnifiedRetriever.reindex_file(path)`)
- Optionally delete vector orphans (`delete_documents_by_source(path)`)
- Update DB rows accordingly (status, chunk_count, vector_count, timestamps)

## Startup Behavior

- During app startup, after vector store is initialized, run a validation pass:
  - Dry-run by default to log mismatches
  - In dev, can run full reconcile automatically; in prod, keep dry-run and expose admin UI action

## Error Handling & Recovery

- `SemanticSearcher` already auto-resets on corruption; after reset, a reconcile pass will rebuild from filesystem
- All reconciliation actions are logged; per-file errors recorded in DB

## Admin UI

- New Consistency view: mismatch counts and actionable lists (reindex/delete)
- Sources view: enriched rows with `status`, `chunk_count`, `vector_count`

## Backward Compatibility

- Keep `index_metadata.json` updates (hash + classification) for now
- Migrate progressively to DB as the authoritative status store

## Security Notes

- Admin-only endpoints require existing session auth guards
- Deletion actions gated behind an explicit `allow_deletes` flag

## Open Questions

- Should we persist classification from `index_metadata.json` into DB? (Phase 2)
- Periodic background sync cadence and toggles per environment

