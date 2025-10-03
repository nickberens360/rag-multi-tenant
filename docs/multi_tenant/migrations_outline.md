# Alembic Initial Schema — Multi‑Tenant (Greenfield)

This document provides an initial, single Alembic revision for a greenfield multi‑tenant schema with Postgres Row‑Level Security (RLS). No backfills or phased migrations are required.

Agent quick links
- Agent Playbook (guide): `docs/multi_tenant/agent_playbook.md`
- Machine-readable index: `docs/multi_tenant/agent_playbook.yaml` (JSON: `docs/multi_tenant/agent_playbook.json`)

Conventions
- Schema: `public`
- GUC for RLS: `app.tenant_id` (UUID string). Set per request via `SET LOCAL app.tenant_id = '<uuid>'`.
- App role: `NOBYPASSRLS` and least privilege.
- Soft‑delete: `deleted_at TIMESTAMPTZ NULL` on select tenant‑scoped tables where recovery is useful.

Initial Revision Skeleton (init_multi_tenant_schema)

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "init_multi_tenant_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Global tables
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),  # FK to users (global) if present
        sa.Column("role", sa.String(length=20), nullable=False),  # owner|admin|member
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_membership_tenant_user", "tenant_memberships", ["tenant_id", "user_id"])

    op.create_table(
        "invitations",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("inviter_user_id", sa.BigInteger, nullable=False),  # FK optional
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_invitations_token", "invitations", ["token"], unique=True)

    # Tenant-scoped domain tables (examples; extend to your domain)
    op.create_table(
        "admin_settings",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("setting_key", sa.String(length=120), nullable=False),
        sa.Column("setting_value", sa.Text, nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.BigInteger, nullable=True),
    )
    op.create_unique_constraint("uq_admin_settings_tenant_key", "admin_settings", ["tenant_id", "setting_key"])
    op.create_index("ix_admin_settings_tenant", "admin_settings", ["tenant_id"])  # hot filter

    op.create_table(
        "followup_categories",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("icon", sa.String(length=64), server_default="help-circle"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_followup_categories_tenant_name", "followup_categories", ["tenant_id", "name"])
    op.create_index("ix_followup_categories_tenant", "followup_categories", ["tenant_id"])  # hot filter

    op.create_table(
        "followup_questions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.BigInteger, nullable=False),  # ensure same-tenant FK in app logic/RLS
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger, nullable=True),
    )
    op.create_index("ix_followup_questions_tenant", "followup_questions", ["tenant_id"])  # hot filter

    op.create_table(
        "welcome_questions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.BigInteger, nullable=True),
    )
    op.create_index("ix_welcome_questions_tenant", "welcome_questions", ["tenant_id"])  # hot filter

    op.create_table(
        "api_keys",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_name", sa.String(length=120), nullable=False),
        sa.Column("key_type", sa.String(length=64), nullable=False),
        sa.Column("encrypted_value", sa.Text, nullable=False),
        sa.Column("last_four", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_validated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by", sa.BigInteger),
    )
    op.create_unique_constraint("uq_api_keys_tenant_name", "api_keys", ["tenant_id", "key_name"])
    op.create_index("ix_api_keys_tenant", "api_keys", ["tenant_id"])  # hot filter

    # Example log-like tables; index by (tenant_id, timestamp)
    op.create_table(
        "query_logs",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_query", sa.Text),
        sa.Column("system_response", sa.Text),
        sa.Column("query_type", sa.String(length=32), server_default="text"),
        sa.Column("response_time_ms", sa.Float),
        sa.Column("llm_provider", sa.String(length=64)),
        sa.Column("llm_model", sa.String(length=64)),
        sa.Column("vector_search_score", sa.Float),
        sa.Column("sources_used", postgresql.JSONB, nullable=True),
        sa.Column("follow_up_questions", postgresql.JSONB, nullable=True),
        sa.Column("cache_hit", sa.Boolean, server_default=sa.text("false")),
        sa.Column("error_occurred", sa.Boolean, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text),
        sa.Column("user_feedback", sa.Text),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("client_ip", sa.Text),
        sa.Column("location_city", sa.Text),
        sa.Column("location_region", sa.Text),
        sa.Column("location_country", sa.Text),
        sa.Column("location_country_code", sa.Text),
    )
    op.create_index("ix_query_logs_tenant_ts", "query_logs", ["tenant_id", "timestamp"])  # hot filter

    op.create_table(
        "content_gaps",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query_pattern", sa.Text, nullable=False),
        sa.Column("occurrence_count", sa.Integer, server_default="0"),
        sa.Column("avg_similarity_score", sa.Float),
        sa.Column("first_seen", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved", sa.Boolean, server_default=sa.text("false")),
        sa.Column("notes", sa.Text),
        sa.Column("sample_query_id", sa.BigInteger),  # ensure same-tenant relationship in policies/logic
    )
    op.create_index("ix_content_gaps_tenant", "content_gaps", ["tenant_id"])  # hot filter

    op.create_table(
        "security_events",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),  # nullable for infra-level events
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("identifier", sa.Text, nullable=False),
        sa.Column("details", sa.Text),
        sa.Column("severity", sa.String(length=16), server_default="low"),
        sa.Column("ip_address", sa.Text),
        sa.Column("user_agent", sa.Text),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_security_events_tenant_type", "security_events", ["tenant_id", "event_type"])  # flexible scope

    # RLS policies for tenant-scoped tables
    TENANT_TABLES = [
        "admin_settings",
        "followup_categories",
        "followup_questions",
        "welcome_questions",
        "api_keys",
        "query_logs",
        "content_gaps",
        # security_events optional (tenant_id nullable); add a policy only if you require row scoping there
    ]

    for table in TENANT_TABLES:
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(
            f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table};"
        ))
        op.execute(sa.text(
            f"""
            CREATE POLICY {table}_tenant_policy ON {table}
              USING (tenant_id = current_setting('app.tenant_id')::uuid)
              WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
            """
        ))


def downgrade():
    # Drop in reverse dependency order
    for table in [
        "content_gaps",
        "query_logs",
        "api_keys",
        "welcome_questions",
        "followup_questions",
        "followup_categories",
        "invitations",
        "tenant_memberships",
        "security_events",
        "admin_settings",
        "tenants",
    ]:
        try:
            op.drop_table(table)
        except Exception:
            pass
```

Smoke Test (psql)
```sql
-- As an app role with RLS enabled
SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000001';
SELECT COUNT(*) FROM admin_settings;  -- should show only default tenant rows

SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000002';
SELECT COUNT(*) FROM admin_settings;  -- should show 0 until seeded for tenant 2
```

Notes
- Create the global `users` table in your auth stack and reference it from memberships as needed.
- Consider `FORCE ROW LEVEL SECURITY` if your database version and security posture require it.
