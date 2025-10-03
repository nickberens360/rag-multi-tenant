"""
Smoke test for tenant-scoped knowledge endpoints without running the full app.

It mounts backend.routes.knowledge under '/{tenant}/api/admin' and injects a
stub unified_retriever that returns deterministic, tenant-tagged documents.
"""

# Ensure repository root is on sys.path for 'backend' package imports
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from backend.routes import knowledge as knowledge_routes


class StubSemanticSearcher:
    def __init__(self):
        # Provide a non-None placeholder so route checks pass
        self.vector_store = object()
        # Create a small in-memory set of docs with tenant metadata
        # Two docs for T1 (acme), one doc for T2 (beta)
        self._docs = [
            {
                "id": "T1-1",
                "content": "Acme content 1",
                "metadata": {
                    "tenant_id": "T1",
                    "tenant_slug": "acme",
                    "scope": "tenant",
                    "source": "backend/knowledge/tenants/acme/documents/a.md",
                    "content_type": "technical",
                },
            },
            {
                "id": "T1-2",
                "content": "Acme content 2 also technical",
                "metadata": {
                    "tenant_id": "T1",
                    "tenant_slug": "acme",
                    "scope": "tenant",
                    "source": "backend/knowledge/tenants/acme/documents/a.md",
                    "content_type": "technical",
                },
            },
            {
                "id": "T2-1",
                "content": "Beta content 1",
                "metadata": {
                    "tenant_id": "T2",
                    "tenant_slug": "beta",
                    "scope": "tenant",
                    "source": "backend/knowledge/tenants/beta/documents/b.md",
                    "content_type": "about",
                },
            },
        ]

    def get_documents(self, where=None, limit=100, offset=0):
        docs = self._docs
        if where:

            def _match(doc):
                md = doc.get("metadata", {})
                for k, v in where.items():
                    if isinstance(v, dict) and "$contains" in v:
                        if v["$contains"] not in str(md.get(k, "")):
                            return False
                    else:
                        if md.get(k) != v:
                            return False
                return True

            docs = [d for d in docs if _match(d)]
        return docs[offset : offset + limit]

    def get_count(self, where=None):
        return len(self.get_documents(where=where, limit=10_000, offset=0))

    def get_document_by_id(self, doc_id: str):
        for d in self._docs:
            if d["id"] == doc_id:
                return d
        return None


class StubUnifiedRetriever:
    def __init__(self):
        self.semantic_searcher = StubSemanticSearcher()


def build_app() -> FastAPI:
    app = FastAPI()

    # Minimal middleware to extract tenant from path and set request.state.tenant_id
    @app.middleware("http")
    async def tenant_state_middleware(request: Request, call_next):
        # Expect path '/{tenant}/api/admin/...'
        parts = (request.url.path or "/").split("/")
        if len(parts) > 1 and parts[1] in {"acme", "beta"}:
            slug = parts[1]
            request.state.tenant_slug = slug
            request.state.tenant_id = {"acme": "T1", "beta": "T2"}.get(slug)
        return await call_next(request)

    # Attach stub unified retriever
    app.state.unified_retriever = StubUnifiedRetriever()

    # Mount the knowledge router under the tenant-prefixed admin path
    app.include_router(knowledge_routes.router, prefix="/{tenant}/api/admin")
    return app


def run_smoke_tests():
    app = build_app()
    client = TestClient(app)

    # 1) Sources for acme (T1): expect only a.md
    r = client.get("/acme/api/admin/knowledge/sources")
    assert r.status_code == 200, r.text
    data = r.json()
    srcs = data.get("sources") or []
    paths = sorted([s.get("path") for s in srcs])
    assert paths == ["backend/knowledge/tenants/acme/documents/a.md"], paths

    # 2) Sources for beta (T2): expect only b.md
    r = client.get("/beta/api/admin/knowledge/sources")
    assert r.status_code == 200, r.text
    data = r.json()
    srcs = data.get("sources") or []
    paths = sorted([s.get("path") for s in srcs])
    assert paths == ["backend/knowledge/tenants/beta/documents/b.md"], paths

    # 3) Documents for acme (T1): expect ids T1-1, T1-2 and tenant-scoped count
    r = client.get("/acme/api/admin/knowledge/documents?limit=50&offset=0")
    assert r.status_code == 200, r.text
    docs_payload = r.json()
    ids = sorted([d.get("id") for d in docs_payload.get("documents", [])])
    assert ids == ["T1-1", "T1-2"], ids
    assert docs_payload.get("total_count") == 2, docs_payload

    # 4) Document content: tenant allowed
    r = client.get("/acme/api/admin/knowledge/documents/T1-1")
    assert r.status_code == 200, r.text

    # 5) Document content: tenant isolation (acme cannot read T2 doc)
    r = client.get("/acme/api/admin/knowledge/documents/T2-1")
    assert r.status_code == 404, r.text

    print("OK: tenant-scoped sources, documents, and per-doc isolation are working")


if __name__ == "__main__":
    run_smoke_tests()
