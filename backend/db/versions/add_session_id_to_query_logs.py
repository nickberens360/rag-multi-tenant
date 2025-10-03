"""Add session_id column to query_logs

Revision ID: add_session_id_to_query_logs
Revises: add_knowledge_files_table
Create Date: 2025-09-26
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_session_id_to_query_logs"
down_revision = "add_knowledge_files_table"
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable session_id to query_logs for grouping by client session/request
    op.add_column("query_logs", sa.Column("session_id", sa.String(length=128), nullable=True))
    # Optional helpful index for grouping/filtering
    try:
        op.create_index("ix_query_logs_session", "query_logs", ["session_id"])
    except Exception:
        # Best-effort; not all dialects require explicit index
        pass


def downgrade():
    try:
        op.drop_index("ix_query_logs_session", table_name="query_logs")
    except Exception:
        pass
    op.drop_column("query_logs", "session_id")
