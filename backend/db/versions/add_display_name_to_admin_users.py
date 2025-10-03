"""Add display_name to admin_users

Revision ID: add_display_name_to_admin_users
Revises: add_admin_users_sessions
Create Date: 2025-09-25
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_display_name_to_admin_users"
down_revision = "add_admin_users_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "admin_users",
        sa.Column("display_name", sa.String(length=100), nullable=True),
    )


def downgrade():
    op.drop_column("admin_users", "display_name")
