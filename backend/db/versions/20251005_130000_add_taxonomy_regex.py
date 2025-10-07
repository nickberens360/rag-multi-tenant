"""Add regex patterns to tenant_taxonomy for query routing

Revision ID: add_taxonomy_regex
Revises: add_taxonomy_bootstrapped_flag
Create Date: 2025-10-05

This migration adds three new columns to tenant_taxonomy:
1. regex: JSONB array of regex patterns for query routing (used by content router)
2. user_created: Boolean flag to track folksonomy tags (Phase 3 prep)
3. usage_count: Integer counter for analytics tracking (Phase 3 prep)

These columns consolidate the dual taxonomy system into a single source of truth.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "add_taxonomy_regex"
down_revision = "add_taxonomy_bootstrapped_flag"
branch_labels = None
depends_on = None


def upgrade():
    """Add regex column for query pattern matching"""

    # Add regex patterns column (JSONB array of regex strings)
    op.add_column(
        "tenant_taxonomy",
        sa.Column(
            "regex",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Regex patterns for query routing (e.g., ['\\\\bproject\\\\b', '\\\\bbuilt\\\\b'])",
        ),
    )

    # Add user_created flag for folksonomy tracking (Phase 3)
    op.add_column(
        "tenant_taxonomy",
        sa.Column(
            "user_created",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="True if created by user (folksonomy), false if official taxonomy",
        ),
    )

    # Add usage_count for analytics (Phase 3)
    op.add_column(
        "tenant_taxonomy",
        sa.Column(
            "usage_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Number of documents tagged with this category",
        ),
    )


def downgrade():
    """Remove added columns"""
    op.drop_column("tenant_taxonomy", "usage_count")
    op.drop_column("tenant_taxonomy", "user_created")
    op.drop_column("tenant_taxonomy", "regex")
