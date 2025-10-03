"""Add rate_limiting table for admin auth (global)

Revision ID: add_rate_limiting_table
Revises: add_taxonomy_settings_history
Create Date: 2025-09-25
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_rate_limiting_table"
down_revision = "add_taxonomy_settings_history"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rate_limiting",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("identifier", sa.String(length=320), nullable=False),
        sa.Column("identifier_type", sa.String(length=32), nullable=False),  # 'ip' or 'username'
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("first_attempt_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_attempt_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("lockout_until", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_unique_constraint("uq_rate_limit_identifier", "rate_limiting", ["identifier", "identifier_type"])
    op.create_index("ix_rate_limit_identifier", "rate_limiting", ["identifier", "identifier_type"])


def downgrade():
    op.drop_index("ix_rate_limit_identifier", table_name="rate_limiting")
    op.drop_constraint("uq_rate_limit_identifier", "rate_limiting", type_="unique")
    op.drop_table("rate_limiting")
