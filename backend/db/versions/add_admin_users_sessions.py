"""Add admin_users and admin_sessions tables

Revision ID: add_admin_users_sessions
Revises: init_multi_tenant_schema
Create Date: 2025-09-25
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_admin_users_sessions"
down_revision = "init_multi_tenant_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_users",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False, unique=True),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_active_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ip_address", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_admin_sessions_user_active", "admin_sessions", ["user_id", "is_active"])


def downgrade():
    op.drop_index("ix_admin_sessions_user_active", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_table("admin_users")
