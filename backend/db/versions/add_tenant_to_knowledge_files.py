"""Add tenant_id to knowledge_files table with RLS

Revision ID: add_tenant_to_knowledge_files
Revises: add_knowledge_files_table
Create Date: 2025-09-28
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_tenant_to_knowledge_files"
down_revision = "add_knowledge_files_table"
branch_labels = None
depends_on = None


def upgrade():
    # Add tenant_id column and scope column
    op.add_column("knowledge_files", sa.Column("tenant_id", sa.UUID, nullable=True))
    op.add_column("knowledge_files", sa.Column("scope", sa.String(16), server_default="shared", nullable=False))

    # Create index on tenant_id for performance
    op.create_index("ix_knowledge_files_tenant_id", "knowledge_files", ["tenant_id"])

    # Create composite unique constraint on (tenant_id, path) to ensure no duplicate paths per tenant
    # First drop the existing unique constraint on path
    op.drop_constraint("knowledge_files_path_key", "knowledge_files", type_="unique")

    # Create new unique constraint on (tenant_id, path)
    op.create_unique_constraint("uq_knowledge_files_tenant_path", "knowledge_files", ["tenant_id", "path"])

    # Enable Row Level Security
    op.execute("ALTER TABLE knowledge_files ENABLE ROW LEVEL SECURITY")

    # Create RLS policy for tenant isolation
    op.execute(
        """
        CREATE POLICY tenant_isolation_knowledge_files ON knowledge_files
        USING (
            tenant_id = COALESCE(
                NULLIF(current_setting('app.tenant_id', true), '')::uuid,
                CAST(current_setting('app.default_tenant_id', true) AS uuid)
            )
            OR scope = 'shared'
        )
    """
    )

    # Create policy for INSERT operations
    op.execute(
        """
        CREATE POLICY tenant_isolation_knowledge_files_insert ON knowledge_files
        FOR INSERT
        WITH CHECK (
            tenant_id = COALESCE(
                NULLIF(current_setting('app.tenant_id', true), '')::uuid,
                CAST(current_setting('app.default_tenant_id', true) AS uuid)
            )
            OR scope = 'shared'
        )
    """
    )


def downgrade():
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation_knowledge_files_insert ON knowledge_files")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_knowledge_files ON knowledge_files")

    # Disable Row Level Security
    op.execute("ALTER TABLE knowledge_files DISABLE ROW LEVEL SECURITY")

    # Drop unique constraint
    op.drop_constraint("uq_knowledge_files_tenant_path", "knowledge_files", type_="unique")

    # Recreate original unique constraint on path
    op.create_unique_constraint("knowledge_files_path_key", "knowledge_files", ["path"])

    # Drop index
    op.drop_index("ix_knowledge_files_tenant_id", table_name="knowledge_files")

    # Drop columns
    op.drop_column("knowledge_files", "scope")
    op.drop_column("knowledge_files", "tenant_id")
