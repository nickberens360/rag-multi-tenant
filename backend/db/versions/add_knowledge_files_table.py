"""Add knowledge_files table (Postgres)

Revision ID: add_knowledge_files_table
Revises: add_user_2fa_table
Create Date: 2025-09-25
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_knowledge_files_table"
down_revision = "add_user_2fa_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "knowledge_files",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("path", sa.Text, nullable=False, unique=True),
        sa.Column("dir", sa.Text),
        sa.Column("filename", sa.Text),
        sa.Column("ext", sa.String(length=16)),
        sa.Column("size", sa.BigInteger),
        sa.Column("mtime", sa.Float),
        sa.Column("hash", sa.Text),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="discovered"),
        sa.Column("chunk_count", sa.Integer, server_default="0"),
        sa.Column("vector_count", sa.Integer, server_default="0"),
        sa.Column("discovered_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("indexed_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_error", sa.Text),
        sa.Column("last_error_at", sa.TIMESTAMP(timezone=True)),
    )
    op.create_index("ix_kf_status", "knowledge_files", ["status"])
    op.create_index("ix_kf_dir", "knowledge_files", ["dir"])


def downgrade():
    op.drop_index("ix_kf_dir", table_name="knowledge_files")
    op.drop_index("ix_kf_status", table_name="knowledge_files")
    op.drop_table("knowledge_files")
