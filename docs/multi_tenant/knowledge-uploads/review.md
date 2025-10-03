# Per‑Tenant RAG Document Sources — Review Findings

Re‑review (2025‑09‑29) — Fixes Applied
- Admin routes are now tenant‑filtered in `backend/routes/knowledge.py`:
  - `GET /knowledge/documents` adds `tenant_id` to `where_clause` and uses `semantic_searcher.get_count(where=...)` for `total_count`.
  - `GET /knowledge/sources` calls `get_documents(where={"tenant_id": tid}, ...)`.
  - `GET /knowledge/documents/{id}` checks `metadata.tenant_id` against the active tenant and returns 404 on mismatch.
- Uploads and DB status endpoints were already tenant‑scoped and remain correct.
- Admin Sources view fallback is now safe because the backend sources endpoint returns only the active tenant’s sources.


This report reviews the per‑tenant RAG “document source” logic across the backend API and the admin frontend, with verification steps and concrete observations. It calls out what’s correct today and the specific places where tenant filtering needs to be tightened.

## Scope
- Backend FastAPI routes touching knowledge documents and sources
- Admin dashboard frontend (tenant switcher, uploads, sources/documents views)
- Data flow for per‑tenant isolation (DB status store, vector store, and paths)

## Summary
- Uploads and DB status are tenant‑scoped and correct.
- Vector store is a single shared collection with tenant metadata in document metadatas.
- Some admin read routes do not filter by tenant_id; the admin UI “sources” page is safe via DB‑first merge, but its fallback can leak cross‑tenant sources. The “documents” page likely shows cross‑tenant documents today.

## Backend Review

- Knowledge uploads (tenant‑aware)
  - POST `/{tenant}/api/admin/knowledge/uploads`
  - GET `/{tenant}/api/admin/knowledge/uploads/status`
  - DELETE `/{tenant}/api/admin/knowledge/uploads/{file_id}`
  - GET `/{tenant}/api/admin/knowledge/uploads/quota`
  - Implementation: `backend/routes/knowledge_uploads.py`
  - Uses `get_tenant_context` to enforce tenant isolation, writes files to `backend/knowledge/tenants/{tenant_slug}/documents`, and records rows in `KnowledgeIndexDB` with `tenant_id` and `scope='tenant'`.
  - Status listing uses `KnowledgeIndexDB.list_files(..., tenant_id=..., include_shared=False)` — correct tenant scoping.

- Knowledge file status (admin consistency)
  - GET `/{tenant}/api/admin/knowledge/files/status`
  - Implementation: `backend/routes/knowledge_admin_sync.py::list_knowledge_files`
  - Seeds DB by scanning filesystem with tenant context, then returns DB rows filtered to the current `tenant_id` — correct.

- Knowledge sources (admin)
  - GET `/{tenant}/api/admin/knowledge/sources`
  - Implementation: `backend/routes/knowledge.py::get_knowledge_sources`
  - Current behavior: fetches all docs from the vector store via `semantic_searcher.get_documents(limit=...)` with no tenant filter. Returns an aggregate of unique sources across all tenants. This is not tenant‑scoped.
  - Impact: Admin frontend uses this endpoint only to enrich items returned from the DB tenant‑scoped status list. It does not introduce new rows, so the displayed list remains tenant‑scoped unless the DB call fails (see Frontend section).

- Knowledge documents listing (admin)
  - GET `/{tenant}/api/admin/knowledge/documents?limit=&offset=`
  - Implementation: `backend/routes/knowledge.py::get_indexed_documents`
  - Current behavior: also calls `semantic_searcher.get_documents(...)` without tenant filter — not tenant‑scoped.
  - Impact: Admin Documents view likely shows documents across all tenants.

- Knowledge stats (admin)
  - GET `/{tenant}/api/admin/knowledge/stats`
  - Implementation: `backend/routes/knowledge.py::get_knowledge_stats`
  - Current behavior: reads `request.state.tenant_id` and applies `where={"tenant_id": tid}` to the vector store — correct.

- Vector store and stamping
  - Implementation: `backend/core/unified_retriever.py` and `backend/core/semantic_searcher.py`
  - Indexing stamps `tenant_id`, `tenant_slug`, `scope="tenant"` for files under `backend/knowledge/tenants/{slug}/documents/...`.
  - `SemanticSearcher` provides generic `get_documents(where=...)` and `get_count_for_tenant(...)`, but does not automatically apply tenant context — callers must pass `where={"tenant_id": tid}`.

- DB status store (Postgres)
  - Implementation: `backend/core/knowledge_index_db.py`
  - All CRUD uses explicit `tenant_id` propagation and a GUC fallback for RLS — correct and consistent.

## Admin Frontend Review

- Tenant base URL
  - Admin API interceptor builds baseURL as `/{tenant}/api/admin` when a tenant is active; otherwise `/api/admin`.
  - Implementation: `admin/frontend/src/services/api.js` (request interceptor + `setCurrentTenant`).

- OrgSwitcher behavior
  - Implementation: `admin/frontend/src/components/OrgSwitcher.vue` and store `admin/frontend/src/stores/tenant.js`.
  - Switch updates `adminAPI.currentTenant` and navigates to the same route under `/{tenant}/...` — correct.

- Sources view
  - Implementation: `admin/frontend/src/views/knowledge/SourcesView.vue`.
  - Data flow:
    - Primary: GET `/{tenant}/api/admin/knowledge/files/status` (DB) — tenant‑scoped list, used to build the rows.
    - Enrichment: GET `/{tenant}/api/admin/knowledge/sources` (vector) — merges by `path`; does not add new rows.
  - Result: Displayed sources reflect only current tenant (derived from DB rows). When switching tenants, the component watches `currentTenant` and reloads — correct.
  - Edge case: If the DB status call fails, it falls back to vector‑only `getKnowledgeSources()`, which is not tenant‑filtered. That fallback would show cross‑tenant sources.

- Documents view
  - Implementation: `admin/frontend/src/views/knowledge/DocumentsView.vue`.
  - Uses GET `/{tenant}/api/admin/knowledge/documents` and displays results directly from the vector store.
  - Since the backend route is not tenant‑filtered, this view likely shows cross‑tenant documents today.

## Validation Checklist (performed)
- Verified per‑tenant upload isolation in `knowledge_uploads.py` (writes to `tenants/{slug}/documents` and records `tenant_id`).
- Confirmed `KnowledgeIndexDB.list_files(..., tenant_id=...)` filters rows by tenant and seeds via `KnowledgeStateSync.scan_filesystem(tenant_id=...)`.
- Confirmed `knowledge.py::get_knowledge_sources` and `get_indexed_documents` do not apply `tenant_id` filter.
- Confirmed admin API base URL includes `/{tenant}/api/admin` and OrgSwitcher updates it.
- Confirmed Sources view merges vector info into the tenant‑scoped DB base list; fallback uses unfiltered vector data.

## Gaps & Recommendations
- Admin “sources” API should be tenant‑filtered to remove fallback risk and simplify frontend logic.
  - In `backend/routes/knowledge.py::get_knowledge_sources`, read `tid = request.state.tenant_id` and call `get_documents(where={"tenant_id": tid}, ...)`.

- Admin “documents” API should be tenant‑filtered.
  - In `backend/routes/knowledge.py::get_indexed_documents`, add `where={"tenant_id": tid}`; keep existing filters additive (e.g., content_type, source).

- Document content by ID should validate tenant.
  - In `backend/routes/knowledge.py::get_document_content`, ensure returned doc’s `metadata.tenant_id` matches `request.state.tenant_id`, otherwise return 404.

- Optional: Public knowledge routes
  - If public endpoints should be tenant‑scoped in multi‑tenant deployments, mirror the above filters in `routes/knowledge_public.py`.

- Tenants router mounting
  - Admin tenants router is mounted at `/api/admin/tenants` (no path‑prefix variant). Current frontend calls it before setting an active tenant so it works, but for consistency consider also mounting it under `/{tenant}/api/admin`.

## What Works Today
- Uploads and status listing: fully tenant‑scoped.
- Sources view when DB endpoint is healthy: only current tenant’s files are shown; vector data is used for enrichment only.
- Stats endpoint already filters by current tenant.

## Where To Tighten
- Add tenant filter to admin `GET /knowledge/sources` and `GET /knowledge/documents`.
- Add tenant validation in `GET /knowledge/documents/{document_id}`.
- Consider scoping public knowledge routes if multi‑tenant public views are planned.

## Quick Test Plan
- Upload a file as Tenant A and another as Tenant B via `/{tenant}/api/admin/knowledge/uploads`.
- In Admin UI:
  - Switch to Tenant A → Sources shows only A’s file; switch to Tenant B → shows only B’s.
  - Documents view: verify after backend fixes it shows only active tenant’s documents.
  - Simulate DB status failure (temporary) and confirm sources still tenant‑scoped once `/knowledge/sources` is filtered.
