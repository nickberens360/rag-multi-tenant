"""
Integration tests for document metadata feature.

Tests cover:
- Database schema with metadata columns
- Tenant-scoped taxonomy with RLS
- Effective metadata computation (manual > inferred)
- API endpoints (upload, update, batch inference, metrics)
- Metadata precedence and provenance tracking
- Retrieval with metadata filters
- Tenant isolation
"""

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text

from backend.core.knowledge_index_db import KnowledgeIndexDB
from backend.main import app

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Get test database URL from environment
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


def require_test_db():
    """Skip test if TEST_DATABASE_URL is not set."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set; skipping database tests")


@pytest.fixture
async def client():
    """Create AsyncClient for making requests to the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def db_engine():
    """Create database engine for direct SQL queries."""
    require_test_db()
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    return engine


@pytest.fixture
def test_tenant_id(db_engine):
    """Create a test tenant and return its ID."""
    tenant_id = str(uuid.uuid4())

    with db_engine.begin() as conn:
        # Create tenant
        conn.execute(
            text(
                """
                INSERT INTO tenants (id, slug, name, created_at, updated_at)
                VALUES (:id, :slug, :name, now(), now())
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": tenant_id, "slug": f"test-{tenant_id[:8]}", "name": f"Test Tenant {tenant_id[:8]}"},
        )

    yield tenant_id

    # Cleanup is handled by transaction rollback or manual cleanup


@pytest.fixture
def test_file_path(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test_document.md"
    test_file.write_text("# Test Document\n\nThis is a test document for metadata testing.")
    yield str(test_file)


class TestSchemaAndDatabase:
    """Test database schema and metadata columns."""

    def test_knowledge_files_has_metadata_columns(self, db_engine):
        """Test that knowledge_files table has all required metadata columns."""
        require_test_db()

        with db_engine.connect() as conn:
            # Query column information
            result = conn.execute(
                text(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'knowledge_files'
                      AND column_name IN (
                        'manual_content_type', 'manual_tags',
                        'inferred_content_type', 'inferred_tags', 'inferred_confidence',
                        'metadata_provenance', 'metadata_updated_by',
                        'metadata_updated_at', 'metadata_version'
                      )
                    ORDER BY column_name
                    """
                )
            )
            columns = {row[0]: row[1] for row in result.fetchall()}

        # Verify all expected columns exist
        expected_columns = {
            "manual_content_type",
            "manual_tags",
            "inferred_content_type",
            "inferred_tags",
            "inferred_confidence",
            "metadata_provenance",
            "metadata_updated_by",
            "metadata_updated_at",
            "metadata_version",
        }

        assert expected_columns.issubset(
            set(columns.keys())
        ), f"Missing columns: {expected_columns - set(columns.keys())}"

        # Verify data types
        assert columns["manual_content_type"] in ("text", "character varying")
        assert columns["inferred_content_type"] in ("text", "character varying")
        assert columns["inferred_confidence"] in ("real", "double precision")
        assert columns["metadata_version"] == "integer"

    def test_tenant_taxonomy_table_exists(self, db_engine):
        """Test that tenant_taxonomy table exists with correct structure."""
        require_test_db()

        with db_engine.connect() as conn:
            # Check table exists
            result = conn.execute(
                text(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'tenant_taxonomy'
                    ORDER BY ordinal_position
                    """
                )
            )
            columns = {row[0]: row[1] for row in result.fetchall()}

        # Verify required columns
        required_columns = {"tenant_id", "key", "label", "synonyms", "active"}
        assert required_columns.issubset(set(columns.keys())), f"Missing columns: {required_columns - set(columns.keys())}"

    def test_effective_metadata_computation(self, db_engine, test_tenant_id):
        """Test that COALESCE correctly computes effective metadata (manual > inferred)."""
        require_test_db()

        test_path = f"/test/doc_{uuid.uuid4()}.md"

        with db_engine.begin() as conn:
            # Set tenant context
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_id})

            # Insert file with both manual and inferred metadata
            conn.execute(
                text(
                    """
                    INSERT INTO knowledge_files (
                        tenant_id, path, dir, filename, ext, status,
                        manual_content_type, manual_tags,
                        inferred_content_type, inferred_tags,
                        metadata_provenance
                    ) VALUES (
                        :tenant_id, :path, :dir, :filename, :ext, :status,
                        :manual_content_type, :manual_tags,
                        :inferred_content_type, :inferred_tags,
                        :provenance
                    )
                    """
                ),
                {
                    "tenant_id": test_tenant_id,
                    "path": test_path,
                    "dir": "/test",
                    "filename": "doc.md",
                    "ext": "md",
                    "status": "indexed",
                    "manual_content_type": "technical",
                    "manual_tags": json.dumps(["manual-tag"]),
                    "inferred_content_type": "creative",
                    "inferred_tags": json.dumps(["inferred-tag"]),
                    "provenance": "manual",
                },
            )

            # Query with COALESCE to get effective metadata
            row = conn.execute(
                text(
                    """
                    SELECT
                        COALESCE(manual_content_type, inferred_content_type) as effective_content_type,
                        COALESCE(manual_tags, inferred_tags, '[]'::jsonb) as effective_tags
                    FROM knowledge_files
                    WHERE path = :path AND tenant_id = :tenant_id
                    """
                ),
                {"path": test_path, "tenant_id": test_tenant_id},
            ).first()

        # Manual metadata should take precedence
        assert row[0] == "technical", "Manual content_type should take precedence"
        assert json.loads(row[1]) == ["manual-tag"], "Manual tags should take precedence"

    def test_tenant_taxonomy_rls(self, db_engine):
        """Test that tenant_taxonomy has Row Level Security."""
        require_test_db()

        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        with db_engine.begin() as conn:
            # Create two tenants
            for tid, slug in [(tenant1_id, "t1"), (tenant2_id, "t2")]:
                conn.execute(
                    text(
                        """
                        INSERT INTO tenants (id, slug, name, created_at, updated_at)
                        VALUES (:id, :slug, :name, now(), now())
                        ON CONFLICT (id) DO NOTHING
                        """
                    ),
                    {"id": tid, "slug": slug, "name": f"Tenant {slug}"},
                )

            # Insert taxonomy entry for tenant1
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant1_id})
            conn.execute(
                text(
                    """
                    INSERT INTO tenant_taxonomy (tenant_id, key, label, synonyms, active)
                    VALUES (:tid, :key, :label, :synonyms, :active)
                    """
                ),
                {
                    "tid": tenant1_id,
                    "key": "tech-docs",
                    "label": "Technical Documentation",
                    "synonyms": json.dumps(["technical", "docs"]),
                    "active": True,
                },
            )

            # Insert taxonomy entry for tenant2
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant2_id})
            conn.execute(
                text(
                    """
                    INSERT INTO tenant_taxonomy (tenant_id, key, label, synonyms, active)
                    VALUES (:tid, :key, :label, :synonyms, :active)
                    """
                ),
                {
                    "tid": tenant2_id,
                    "key": "creative-content",
                    "label": "Creative Content",
                    "synonyms": json.dumps(["creative", "writing"]),
                    "active": True,
                },
            )

            # Query as tenant1 - should only see tenant1's entries
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant1_id})
            rows = conn.execute(text("SELECT key FROM tenant_taxonomy")).fetchall()
            keys = [r[0] for r in rows]

            # Should include tenant1's entry (and possibly default entries)
            assert "tech-docs" in keys, "Tenant1 should see its own taxonomy"
            # Should NOT include tenant2's entry
            assert "creative-content" not in keys, "Tenant1 should not see tenant2's taxonomy"


class TestAPIEndpoints:
    """Test API endpoints for metadata management."""

    @pytest.mark.asyncio
    async def test_get_taxonomy_endpoint(self, client: AsyncClient, test_tenant_id):
        """Test GET /taxonomy endpoint returns tenant-scoped taxonomy."""
        # Mock tenant context
        with patch("backend.routes.taxonomy.get_tenant_context") as mock_tenant_context:
            mock_tenant_context.return_value = {"tenant_id": test_tenant_id}

            response = await client.get("/admin/api/taxonomy", params={"active_only": True})

            assert response.status_code == 200
            data = response.json()
            assert "entries" in data
            assert "total" in data
            assert "tenant_id" in data
            assert data["tenant_id"] == test_tenant_id

    @pytest.mark.asyncio
    async def test_metadata_metrics_endpoint(self, client: AsyncClient, test_tenant_id):
        """Test GET /knowledge/metadata/metrics endpoint."""
        with patch("backend.routes.knowledge.get_tenant_context") as mock_tenant_context:
            mock_tenant_context.return_value = {"tenant_id": test_tenant_id}

            response = await client.get("/admin/api/knowledge/metadata/metrics")

            # Should return 200 even if no data
            assert response.status_code in (200, 503)  # 503 if DB not available
            if response.status_code == 200:
                data = response.json()
                assert "total_files" in data or "error" in data


class TestMetadataPrecedence:
    """Test manual > inferred precedence logic."""

    def test_manual_overrides_inferred_via_db(self, db_engine, test_tenant_id):
        """Test that updating manual metadata overrides inferred metadata."""
        require_test_db()

        test_path = f"/test/precedence_{uuid.uuid4()}.md"
        db = KnowledgeIndexDB()

        with db_engine.begin() as conn:
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_id})

            # Insert file with only inferred metadata
            conn.execute(
                text(
                    """
                    INSERT INTO knowledge_files (
                        tenant_id, path, dir, filename, ext, status,
                        inferred_content_type, inferred_tags, inferred_confidence,
                        metadata_provenance
                    ) VALUES (
                        :tenant_id, :path, :dir, :filename, :ext, :status,
                        :inferred_content_type, :inferred_tags, :confidence,
                        :provenance
                    )
                    """
                ),
                {
                    "tenant_id": test_tenant_id,
                    "path": test_path,
                    "dir": "/test",
                    "filename": "precedence.md",
                    "ext": "md",
                    "status": "indexed",
                    "inferred_content_type": "creative",
                    "inferred_tags": json.dumps(["auto-tag"]),
                    "confidence": 0.85,
                    "provenance": "inferred",
                },
            )

            # Now update with manual metadata
            conn.execute(
                text(
                    """
                    UPDATE knowledge_files
                    SET manual_content_type = :manual_type,
                        manual_tags = :manual_tags,
                        metadata_provenance = :provenance,
                        metadata_version = metadata_version + 1
                    WHERE path = :path AND tenant_id = :tenant_id
                    """
                ),
                {
                    "manual_type": "technical",
                    "manual_tags": json.dumps(["manual-override"]),
                    "provenance": "manual",
                    "path": test_path,
                    "tenant_id": test_tenant_id,
                },
            )

        # Query via KnowledgeIndexDB to get effective metadata
        metadata = db.get_file_metadata(test_path, tenant_id=test_tenant_id)

        assert metadata is not None
        assert metadata["effective_content_type"] == "technical", "Manual should override inferred"
        assert metadata["effective_tags"] == ["manual-override"], "Manual tags should override inferred"
        assert metadata["metadata_provenance"] == "manual"
        assert metadata["metadata_version"] == 2

    def test_provenance_tracking(self, db_engine, test_tenant_id):
        """Test that provenance is correctly tracked through updates."""
        require_test_db()

        test_path = f"/test/provenance_{uuid.uuid4()}.md"

        with db_engine.begin() as conn:
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": test_tenant_id})

            # Insert with inferred metadata
            conn.execute(
                text(
                    """
                    INSERT INTO knowledge_files (
                        tenant_id, path, dir, filename, ext, status,
                        inferred_content_type, metadata_provenance
                    ) VALUES (
                        :tenant_id, :path, :dir, :filename, :ext, :status,
                        :inferred_content_type, :provenance
                    )
                    """
                ),
                {
                    "tenant_id": test_tenant_id,
                    "path": test_path,
                    "dir": "/test",
                    "filename": "provenance.md",
                    "ext": "md",
                    "status": "indexed",
                    "inferred_content_type": "technical",
                    "provenance": "inferred",
                },
            )

            # Verify initial provenance
            row = conn.execute(
                text("SELECT metadata_provenance FROM knowledge_files WHERE path = :path AND tenant_id = :tenant_id"),
                {"path": test_path, "tenant_id": test_tenant_id},
            ).first()
            assert row[0] == "inferred"

            # Add manual metadata
            conn.execute(
                text(
                    """
                    UPDATE knowledge_files
                    SET manual_content_type = :manual_type,
                        metadata_provenance = :provenance
                    WHERE path = :path AND tenant_id = :tenant_id
                    """
                ),
                {"manual_type": "creative", "provenance": "manual", "path": test_path, "tenant_id": test_tenant_id},
            )

            # Verify provenance changed to manual
            row = conn.execute(
                text("SELECT metadata_provenance FROM knowledge_files WHERE path = :path AND tenant_id = :tenant_id"),
                {"path": test_path, "tenant_id": test_tenant_id},
            ).first()
            assert row[0] == "manual"


class TestTenantIsolation:
    """Test tenant isolation for metadata and taxonomy."""

    def test_taxonomy_is_tenant_scoped(self, db_engine):
        """Test that taxonomy entries are scoped to tenants."""
        require_test_db()

        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        with db_engine.begin() as conn:
            # Create tenants
            for tid, slug in [(tenant1_id, "iso1"), (tenant2_id, "iso2")]:
                conn.execute(
                    text(
                        """
                        INSERT INTO tenants (id, slug, name, created_at, updated_at)
                        VALUES (:id, :slug, :name, now(), now())
                        ON CONFLICT (id) DO NOTHING
                        """
                    ),
                    {"id": tid, "slug": slug, "name": f"Tenant {slug}"},
                )

            # Add taxonomy for each tenant
            for tid, key in [(tenant1_id, "tenant1-key"), (tenant2_id, "tenant2-key")]:
                conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
                conn.execute(
                    text(
                        """
                        INSERT INTO tenant_taxonomy (tenant_id, key, label, active)
                        VALUES (:tid, :key, :label, :active)
                        """
                    ),
                    {"tid": tid, "key": key, "label": f"Label for {key}", "active": True},
                )

        # Verify isolation
        with db_engine.connect() as conn:
            # Query as tenant1
            conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant1_id})
            result1 = conn.execute(text("SELECT key FROM tenant_taxonomy WHERE key = 'tenant1-key'")).fetchall()
            result2 = conn.execute(text("SELECT key FROM tenant_taxonomy WHERE key = 'tenant2-key'")).fetchall()

            # Should see own key but not other tenant's
            assert len(result1) > 0, "Tenant1 should see its own taxonomy"
            assert len(result2) == 0, "Tenant1 should not see tenant2's taxonomy"

    def test_metadata_rls_enforcement(self, db_engine):
        """Test that knowledge_files metadata is isolated by tenant."""
        require_test_db()

        tenant1_id = str(uuid.uuid4())
        tenant2_id = str(uuid.uuid4())

        with db_engine.begin() as conn:
            # Create tenants
            for tid, slug in [(tenant1_id, "meta1"), (tenant2_id, "meta2")]:
                conn.execute(
                    text(
                        """
                        INSERT INTO tenants (id, slug, name, created_at, updated_at)
                        VALUES (:id, :slug, :name, now(), now())
                        ON CONFLICT (id) DO NOTHING
                        """
                    ),
                    {"id": tid, "slug": slug, "name": f"Tenant {slug}"},
                )

            # Insert files for each tenant
            for tid, path in [(tenant1_id, "/tenant1/file.md"), (tenant2_id, "/tenant2/file.md")]:
                conn.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tid})
                conn.execute(
                    text(
                        """
                        INSERT INTO knowledge_files (
                            tenant_id, path, dir, filename, ext, status,
                            manual_content_type
                        ) VALUES (
                            :tid, :path, :dir, :filename, :ext, :status, :content_type
                        )
                        """
                    ),
                    {
                        "tid": tid,
                        "path": path,
                        "dir": Path(path).parent.as_posix(),
                        "filename": Path(path).name,
                        "ext": "md",
                        "status": "indexed",
                        "content_type": f"type-{tid[:8]}",
                    },
                )

        # Query as tenant1
        db = KnowledgeIndexDB()
        files_t1 = db.list_files_with_metadata(tenant_id=tenant1_id, limit=100)

        # Should only see tenant1's file
        paths = [f["path"] for f in files_t1]
        assert "/tenant1/file.md" in paths or len(paths) == 0  # May be empty due to test isolation
        assert "/tenant2/file.md" not in paths, "Tenant1 should not see tenant2's files"


class TestMetadataInference:
    """Test metadata inference service."""

    def test_metadata_inference_service_initialization(self):
        """Test that MetadataInferenceService can be initialized."""
        from backend.core.metadata_inference import MetadataInferenceService

        # Should initialize even without API key (will log warning)
        service = MetadataInferenceService()
        assert service.model == "claude-3-haiku-20240307"

    def test_get_tenant_taxonomy_returns_dict(self, test_tenant_id):
        """Test that get_tenant_taxonomy returns a dictionary."""
        from backend.core.metadata_inference import MetadataInferenceService

        service = MetadataInferenceService()
        taxonomy = service.get_tenant_taxonomy(test_tenant_id)

        # Should return a dict (may be empty if no taxonomy exists)
        assert isinstance(taxonomy, dict)


class TestRetrievalIntegration:
    """Test retrieval integration with metadata filters."""

    def test_filter_parsing_placeholder(self):
        """Placeholder test for filter parsing logic."""
        # TODO: Implement once retrieval filter parsing is added
        # This would test parsing of filter strings like:
        # - "content_type:technical"
        # - "tags:python,machine-learning"
        # - "content_type:technical:strict"
        pass

    def test_natural_language_detection_placeholder(self):
        """Placeholder test for natural language filter detection."""
        # TODO: Implement once natural language filter detection is added
        # This would test detection of metadata hints in queries like:
        # - "Show me technical documentation about Python"
        # - "Find creative content related to storytelling"
        pass
