# Context: Tenant‑Aware Knowledge Uploads (Single Vector Store)

Current state (observed)
- Vector store: single Chroma collection (`unified_knowledge`) without tenant filtering by default in `semantic_searcher.py`.
- Unified retriever: present (`unified_retriever_old.py` path) but not tenant‑aware by default.
- Metadata DB: `knowledge_index_db.py` tracks files without a `tenant_id` column yet.
- Sync: `knowledge_admin_sync.py` + `knowledge_state_sync.py` validate and reconcile knowledge state without tenant filtering.

Goal
- Keep a single vector store and enforce tenant isolation via metadata (`tenant_id`, `tenant_slug`) on every chunk; apply `where={"tenant_id": <uuid>}` on all vector reads/writes.
- Track files per tenant in Postgres (`knowledge_files.tenant_id`) with RLS and explicit filters.
- Provide upload endpoints that store files under tenant‑prefixed paths and enqueue indexing that stamps tenant metadata.

Directory layout
- `backend/knowledge/tenants/{tenant-slug}/documents/`
- `backend/knowledge/shared/documents/`

This preserves clear filesystem isolation and quotas while the vector layer remains a single collection filtered by `tenant_id`.

Non‑goals
- Do not introduce a separate Chroma DB per tenant.
- Do not change embedding models or introduce new dependencies.

Key patterns
- Vector writes: wrap additions with `add_documents_for_tenant(docs, tenant_id, tenant_slug)` to stamp metadata.
- Vector reads: wrap retrieval with `similarity_search_with_score_for_tenant(query, tenant_id, k)`.
- SQL reads/writes: add `WHERE tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))` to all queries on tenant‑scoped tables and pass `:fallback_tid`.

Security and limits
- Validate file types and sizes on upload; set reasonable per‑tenant quotas.
- Sanitize paths; never trust client‑supplied paths. Always write under `backend/knowledge/tenants/{slug}/documents/`.
- Optional AV scan (e.g., ClamAV) for uploaded binaries; reject on detection.
- Enforce membership/roles for admin upload endpoints; audit log with tenant context.
