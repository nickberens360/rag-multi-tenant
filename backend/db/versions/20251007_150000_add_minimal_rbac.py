"""Add minimal RBAC tables (roles, permissions, role_permissions, user_roles)

Revision ID: add_minimal_rbac
Revises: migrate_legacy_taxonomy
Create Date: 2025-10-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_minimal_rbac"
down_revision = "migrate_legacy_taxonomy"
branch_labels = None
depends_on = None


def upgrade():
    # permissions catalog
    op.create_table(
        "permissions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # roles (platform or tenant-scoped)
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False, server_default="tenant"),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("built_in", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Enforce scope values
    op.create_check_constraint(
        "roles_scope_check",
        "roles",
        "scope IN ('platform', 'tenant')",
    )

    # Uniqueness: one name per tenant; and unique name for platform roles (tenant_id IS NULL)
    op.create_unique_constraint("uq_roles_tenant_name", "roles", ["tenant_id", "name"])
    op.create_index(
        "uq_roles_platform_name",
        "roles",
        ["name"],
        unique=True,
        postgresql_where=sa.text("tenant_id IS NULL"),
    )

    # role -> permissions (many-to-many)
    op.create_table(
        "role_permissions",
        sa.Column(
            "role_id",
            sa.BigInteger,
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_id",
            sa.BigInteger,
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # user -> roles (assign platform or tenant role)
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.BigInteger, sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=True,
        ),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_by", sa.BigInteger, nullable=True),
    )

    op.create_index("ix_user_roles_user_tenant", "user_roles", ["user_id", "tenant_id"])


def downgrade():
    op.drop_index("ix_user_roles_user_tenant", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_index("uq_roles_platform_name", table_name="roles")
    op.drop_constraint("uq_roles_tenant_name", "roles", type_="unique")
    op.drop_constraint("roles_scope_check", "roles", type_="check")
    op.drop_table("roles")
    op.drop_table("permissions")

