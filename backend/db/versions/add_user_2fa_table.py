"""Add user_2fa table for two-factor auth (global)

Revision ID: add_user_2fa_table
Revises: add_rate_limiting_table
Create Date: 2025-09-25
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_user_2fa_table"
down_revision = "add_rate_limiting_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_2fa",
        sa.Column("user_id", sa.BigInteger, primary_key=True),
        sa.Column("secret", sa.String(length=160), nullable=False),
        sa.Column("backup_codes", sa.Text, nullable=True),  # comma-separated
        sa.Column("used_backup_codes", sa.Text, nullable=True),  # comma-separated
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_2fa_admin_users",
        source_table="user_2fa",
        referent_table="admin_users",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("fk_user_2fa_admin_users", "user_2fa", type_="foreignkey")
    op.drop_table("user_2fa")
