"""Add document metadata for manual and inferred classification

Revision ID: add_document_metadata
Revises: add_tenant_customization_fields
Create Date: 2025-10-05

This migration adds document-level metadata fields to support user-defined
content types and tags with LLM fallback inference. Includes tenant-scoped
taxonomy for controlled vocabulary and provenance tracking.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_document_metadata"
down_revision = "add_tenant_customization_fields"
branch_labels = None
depends_on = None


def upgrade():
    """Add document metadata fields and tenant taxonomy table"""

    # Add metadata columns to knowledge_files table
    op.add_column(
        "knowledge_files",
        sa.Column("manual_content_type", sa.Text, nullable=True),
    )
    op.add_column(
        "knowledge_files",
        sa.Column(
            "manual_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "knowledge_files",
        sa.Column("inferred_content_type", sa.Text, nullable=True),
    )
    op.add_column(
        "knowledge_files",
        sa.Column(
            "inferred_tags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "knowledge_files",
        sa.Column("inferred_confidence", sa.REAL, nullable=True),
    )
    op.add_column(
        "knowledge_files",
        sa.Column(
            "metadata_provenance",
            sa.Text,
            nullable=False,
            server_default="inferred",
        ),
    )
    op.add_column(
        "knowledge_files",
        sa.Column(
            "metadata_updated_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "knowledge_files",
        sa.Column(
            "metadata_updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "knowledge_files",
        sa.Column(
            "metadata_version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
    )

    # Add check constraint for metadata_provenance
    op.create_check_constraint(
        "knowledge_files_metadata_provenance_check",
        "knowledge_files",
        "metadata_provenance IN ('manual', 'inferred', 'mixed')",
    )

    # Create index on metadata fields for query performance
    op.create_index(
        "ix_knowledge_files_manual_content_type",
        "knowledge_files",
        ["manual_content_type"],
    )
    op.create_index(
        "ix_knowledge_files_inferred_content_type",
        "knowledge_files",
        ["inferred_content_type"],
    )

    # Create tenant_taxonomy table for controlled vocabulary
    op.create_table(
        "tenant_taxonomy",
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.Text, nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column(
            "synonyms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "active",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("tenant_id", "key"),
    )

    # Create index on tenant_taxonomy for lookups
    op.create_index(
        "ix_tenant_taxonomy_tenant_active",
        "tenant_taxonomy",
        ["tenant_id", "active"],
    )

    # Enable RLS for tenant isolation
    op.execute(sa.text("ALTER TABLE tenant_taxonomy ENABLE ROW LEVEL SECURITY"))

    # Drop existing policy if present
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_taxonomy_tenant_policy ON tenant_taxonomy;"))

    # Create RLS policy for tenant isolation
    op.execute(
        sa.text(
            """
            CREATE POLICY tenant_taxonomy_tenant_policy ON tenant_taxonomy
              USING (
                tenant_id = COALESCE(
                  NULLIF(current_setting('app.tenant_id', true), '')::uuid,
                  CAST(current_setting('app.default_tenant_id', true) AS uuid)
                )
              )
              WITH CHECK (
                tenant_id = COALESCE(
                  NULLIF(current_setting('app.tenant_id', true), '')::uuid,
                  CAST(current_setting('app.default_tenant_id', true) AS uuid)
                )
              );
            """
        )
    )

    # Create trigger function for updated_at
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION update_tenant_taxonomy_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
    )

    # Create trigger
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trigger_update_tenant_taxonomy_updated_at
            BEFORE UPDATE ON tenant_taxonomy
            FOR EACH ROW
            EXECUTE FUNCTION update_tenant_taxonomy_updated_at();
            """
        )
    )

    # NOTE: Taxonomy seeding removed in favor of optional template bootstrap
    # New tenants should use POST /api/admin/taxonomy/bootstrap to populate taxonomy
    # from industry-specific templates (software, legal, medical, marketing, or empty).
    #
    # Existing tenants with taxonomy already seeded are unaffected.
    # See: docs/multi_tenant/taxonomy-refactor/02-implementation-plan.md

    # LEGACY SEEDING (DISABLED):
    # The following INSERT was removed to allow flexible tenant-specific taxonomies.
    # If you need to re-enable for development, uncomment the block below.

    # op.execute(
    #     sa.text(
    #         """
    #         INSERT INTO tenant_taxonomy (tenant_id, key, label, synonyms)
    #         SELECT
    #             id as tenant_id,
    #             'technical' as key,
    #             'Technical Documentation' as label,
    #             '["documentation", "docs", "guide", "reference"]'::jsonb as synonyms
    #         FROM tenants
    #         WHERE slug = 'default'
    #         UNION ALL
    #         SELECT
    #             id,
    #             'experience',
    #             'Experience & Projects',
    #             '["portfolio", "work", "projects", "case-study"]'::jsonb
    #         FROM tenants
    #         WHERE slug = 'default'
    #         UNION ALL
    #         SELECT
    #             id,
    #             'creative',
    #             'Creative Content',
    #             '["blog", "writing", "article", "content"]'::jsonb
    #         FROM tenants
    #         WHERE slug = 'default'
    #         UNION ALL
    #         SELECT
    #             id,
    #             'personal',
    #             'Personal Information',
    #             '["bio", "about", "resume", "cv"]'::jsonb
    #         FROM tenants
    #         WHERE slug = 'default';
    #         """
    #     )
    # )


def downgrade():
    """Remove document metadata fields and tenant taxonomy table"""

    # Drop trigger and function
    op.execute(sa.text("DROP TRIGGER IF EXISTS trigger_update_tenant_taxonomy_updated_at ON tenant_taxonomy;"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS update_tenant_taxonomy_updated_at();"))

    # Drop RLS policy
    op.execute(sa.text("DROP POLICY IF EXISTS tenant_taxonomy_tenant_policy ON tenant_taxonomy;"))

    # Disable RLS
    op.execute(sa.text("ALTER TABLE tenant_taxonomy DISABLE ROW LEVEL SECURITY"))

    # Drop indexes
    op.drop_index("ix_tenant_taxonomy_tenant_active", table_name="tenant_taxonomy")

    # Drop tenant_taxonomy table
    op.drop_table("tenant_taxonomy")

    # Drop indexes on knowledge_files
    op.drop_index("ix_knowledge_files_inferred_content_type", table_name="knowledge_files")
    op.drop_index("ix_knowledge_files_manual_content_type", table_name="knowledge_files")

    # Drop check constraint
    op.drop_constraint("knowledge_files_metadata_provenance_check", "knowledge_files")

    # Drop metadata columns from knowledge_files
    op.drop_column("knowledge_files", "metadata_version")
    op.drop_column("knowledge_files", "metadata_updated_at")
    op.drop_column("knowledge_files", "metadata_updated_by")
    op.drop_column("knowledge_files", "metadata_provenance")
    op.drop_column("knowledge_files", "inferred_confidence")
    op.drop_column("knowledge_files", "inferred_tags")
    op.drop_column("knowledge_files", "inferred_content_type")
    op.drop_column("knowledge_files", "manual_tags")
    op.drop_column("knowledge_files", "manual_content_type")
