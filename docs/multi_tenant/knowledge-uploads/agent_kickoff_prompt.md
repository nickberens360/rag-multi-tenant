Multi‑Tenant Knowledge Uploads — Agent Prompt (Single Store with tenant_id)

Goal
- Implement tenant‑aware knowledge uploads and retrieval using a single Chroma collection, isolating tenants via strict metadata filtering (`tenant_id`) across indexing and query paths.

Context files to read first
- docs/multi_tenant/knowledge-uploads/issues/README.md
- docs/multi_tenant/knowledge-uploads/issues/CONTEXT.md
- docs/multi_tenant/knowledge-uploads/issues/tasks.yaml (canonical tasks)
- docs/multi_tenant/knowledge-uploads/issues/PROGRESS.yaml (what’s pending)
- docs/multi_tenant/agent_playbook.md (for general tenancy patterns)

Scope to implement now (pending in PROGRESS.yaml)
1) knowledge_vector_single_store_tenant_metadata
2) knowledge_indexer_add_tenant_meta
3) knowledge_retriever_tenant_filtered_search
4) knowledge_db_add_tenant_id_rls
5) knowledge_upload_endpoints
6) knowledge_sync_tenant_filter

Design
- Keep a single Chroma collection (`unified_knowledge`). Add `tenant_id` and `tenant_slug` to every chunk’s metadata during indexing.
- All reads/writes to the vector store must include a `where={"tenant_id": <uuid>}` filter (or equivalent on exposed APIs).
- Shared content: include as `scope=shared` and union results (tenant + shared) at retrieval, then re‑rank top‑K by distance.
- Track files per tenant in Postgres table `knowledge_files` with `tenant_id`; enforce RLS and explicit tenant filters even with RLS.

Directory layout
- `backend/knowledge/tenants/{tenant-slug}/documents/`
- `backend/knowledge/shared/documents/`

This keeps filesystem isolation and quotas simple while the vector layer remains a single collection filtered by `tenant_id`.

Code sketches

1) SemanticSearcher — tenant‑aware add + search
```python
# backend/core/semantic_searcher.py
from langchain.docstore.document import Document

class SemanticSearcher:
    ...
    def add_documents_for_tenant(self, documents: list[Document], tenant_id: str, tenant_slug: str | None = None) -> None:
        if not documents or self.vector_store is None:
            return
        sanitized_docs = []
        for d in documents:
            md = dict(d.metadata or {})
            md["tenant_id"] = tenant_id
            if tenant_slug:
                md["tenant_slug"] = tenant_slug
            sanitized_docs.append(Document(page_content=d.page_content, metadata=self._sanitize_metadata(md)))
        self.vector_store.add_documents(sanitized_docs)

    def similarity_search_with_score_for_tenant(self, query: str, tenant_id: str, k: int | None = None):
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        if k is None:
            from .config_v2 import AppConfig
            k = AppConfig.DEFAULT_SEARCH_K
        where = {"tenant_id": tenant_id}
        # If supporting shared content, perform two queries and merge
        return self.vector_store.similarity_search_with_score(query, k=k, filter=where)
```

2) Unified Retriever — thread tenant through
```python
# backend/core/unified_retriever*.py (wherever queries are dispatched)
def search(self, query: str, *, tenant_id: str, k: int | None = None):
    return self.semantic_searcher.similarity_search_with_score_for_tenant(query, tenant_id=tenant_id, k=k)
```

3) Indexer — stamp tenant metadata on chunks
```python
# Wherever chunks are created before add_documents
chunks = splitter.split_documents(docs)
for c in chunks:
    c.metadata.update({
        "tenant_id": tenant_id,
        "tenant_slug": tenant_slug,
        "source": str(file_path),
        "scope": "tenant",  # or "shared" for global content
    })
searcher.add_documents_for_tenant(chunks, tenant_id=tenant_id, tenant_slug=tenant_slug)
```

4) DB schema — knowledge_files
```sql
-- Alembic: add tenant_id and secure with RLS
ALTER TABLE knowledge_files ADD COLUMN IF NOT EXISTS tenant_id uuid;
ALTER TABLE knowledge_files ADD COLUMN IF NOT EXISTS scope text DEFAULT 'tenant' NOT NULL;
ALTER TABLE knowledge_files ADD CONSTRAINT uq_knowledge_files_tenant_path UNIQUE (tenant_id, path);
CREATE INDEX IF NOT EXISTS idx_knowledge_files_tenant ON knowledge_files(tenant_id);
-- RLS
ALTER TABLE knowledge_files ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON knowledge_files
  USING (tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid,
                              CAST(current_setting('app.default_tenant_id', true) AS uuid)));
```

Anchors and search hints
- Tenant context (pass through to search):
  - search: `rg -n "request.state.tenant_id|tenant_id\s*=\s*request\.state" backend`
- Vector writes/reads entry points:
  - search: `rg -n "add_documents\(|similarity_search_with_score\(" backend/core`
- Knowledge DB queries (add tenant filters):
  - search: `rg -n "FROM knowledge_files|INSERT INTO knowledge_files|UPDATE knowledge_files" backend`
- Sync code touching vector store counts/gets:
  - search: `rg -n "_collection.get\(|collection.get\(" backend/core/knowledge_state_sync.py`

API sketches (admin)
- POST `/{tenant}/api/admin/knowledge/uploads`
  - multipart form-data: `file`, optional `path`
  - saves to `backend/knowledge/tenants/{slug}/documents/...`
  - returns `{ id, path, status }`
- GET `/{tenant}/api/admin/knowledge/uploads/status?limit=50`
  - returns recent files + statuses for the tenant

Quick curl examples
```bash
curl -F "file=@/path/to/doc.pdf" \
  http://localhost:8000/acme/api/admin/knowledge/uploads

curl "http://localhost:8000/acme/api/admin/knowledge/uploads/status?limit=20"
```

Validation checklist
- Grep checks:
  - `rg -n "add_documents_for_tenant\(|similarity_search_with_score_for_tenant\(" backend/core/semantic_searcher.py`
  - `rg -n "tenant_id" backend/core/unified_retriever` (ensure calls pass tenant_id)
  - `rg -n "FROM knowledge_files|INSERT INTO knowledge_files|UPDATE knowledge_files" backend/core/knowledge_index_db.py` with explicit tenant filters
- Manual queries:
  - Upload a file under tenant A, verify A can retrieve and tenant B cannot.
  - Ensure shared content appears to all tenants when enabled.

Progress update
- After implementing and validating, update `docs/multi_tenant/knowledge-uploads/issues/PROGRESS.yaml` to mark tasks completed and add brief notes.

Constraints
- Do not introduce new dependencies.
- Keep changes minimal and consistent with current patterns (e.g., explicit tenant filters in SQL, request.state.tenant_id for context).
