"""Add taxonomy_bootstrapped flag to track onboarding status

Revision ID: add_taxonomy_bootstrapped_flag
Revises: add_document_metadata
Create Date: 2025-10-05
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_taxonomy_bootstrapped_flag"
down_revision = "add_document_metadata"
branch_labels = None
depends_on = None


def upgrade():
    """Add taxonomy_bootstrapped column to tenants table"""

    # Add column to track if tenant has completed taxonomy setup
    op.add_column(
        "tenants",
        sa.Column(
            "taxonomy_bootstrapped",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
    )

    # Mark existing tenants with taxonomy as bootstrapped
    op.execute(
        sa.text(
            """
            UPDATE tenants
            SET taxonomy_bootstrapped = true
            WHERE id IN (
                SELECT DISTINCT tenant_id FROM tenant_taxonomy
            );
            """
        )
    )


def downgrade():
    """Remove taxonomy_bootstrapped column"""
    op.drop_column("tenants", "taxonomy_bootstrapped")
