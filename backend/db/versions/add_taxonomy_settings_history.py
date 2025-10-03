"""Add taxonomy_settings_history table (tenant-scoped)

Revision ID: add_taxonomy_settings_history
Revises: add_display_name_to_admin_users
Create Date: 2025-09-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_taxonomy_settings_history"
down_revision = "add_display_name_to_admin_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "taxonomy_settings_history",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("settings_json", sa.Text, nullable=False),
        sa.Column("category_count", sa.Integer, server_default="0"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.BigInteger, nullable=True),
    )
    op.create_index(
        "ix_taxonomy_settings_history_tenant_created",
        "taxonomy_settings_history",
        ["tenant_id", "created_at"],
    )

    # Enable RLS for tenant isolation
    op.execute(sa.text("ALTER TABLE taxonomy_settings_history ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("DROP POLICY IF EXISTS taxonomy_settings_history_tenant_policy ON taxonomy_settings_history;"))
    op.execute(
        sa.text(
            """
            CREATE POLICY taxonomy_settings_history_tenant_policy ON taxonomy_settings_history
              USING (tenant_id = current_setting('app.tenant_id')::uuid)
              WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
            """
        )
    )


def downgrade():
    op.drop_index("ix_taxonomy_settings_history_tenant_created", table_name="taxonomy_settings_history")
    op.drop_table("taxonomy_settings_history")
