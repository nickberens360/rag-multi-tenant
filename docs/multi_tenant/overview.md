# Multi‑Tenant Overview (Greenfield)

Status

- Greenfield plan: implement Postgres + SQLAlchemy + RLS from day one.

Quick start for agents
- See the Agent Playbook with machine-readable steps: `docs/multi_tenant/agent_playbook.md`.
- Prefer the YAML index for ingestion: `docs/multi_tenant/agent_playbook.yaml` (JSON: `docs/multi_tenant/agent_playbook.json`).
- Implementation code examples: `docs/multi_tenant/implementation_code.md`
- Configuration templates: `docs/multi_tenant/config_templates.md`
- Test specifications: `docs/multi_tenant/test_specifications.md`

Greenfield mode
- Adopt Postgres + SQLAlchemy + RLS from day one. See `plan.md` for the phases.

This document outlines the architectural approach to evolve the app into a multi‑tenant SaaS with a minimal MVP scope and a strong security baseline. No billing or pricing plans are included at this stage.

## Goals
- Isolate tenant data reliably at the database level.
- Minimize app‑wide changes by centralizing tenant resolution and scoping.
- Keep developer ergonomics high: defaults enforce tenancy; opt‑out only for truly global data.
 

## Tenancy Model
- Model: single Postgres database, shared schema, every tenant‑scoped table has `tenant_id` (UUID, NOT NULL, indexed).
- Security: PostgreSQL Row‑Level Security (RLS) enforced on all tenant tables.
- Identity: tenants are “organizations”. Users can belong to multiple tenants with roles (`owner`, `admin`, `member`).



## Tenant Resolution
- Primary: subdomain `https://<tenant>.yourapp.com` for production.
- Fallback (MVP/dev): path prefix `/:tenant/...` for local and early environments without DNS.
- Precedence: subdomain wins; if absent, accept path prefix; if neither present, use default tenant only when a feature flag is enabled (otherwise 404/400, route-dependent).
- Backend determines the current tenant per request, stores it in request context, and sets `SET LOCAL app.tenant_id = '<uuid>'` on the DB session so RLS can use `current_setting('app.tenant_id')`.
- Headers like `X-Tenant` may be used for client convenience in early dev but are not trusted for security.



## Data Model Additions
- New tables:
  - `tenants`: id (UUID PK), slug (unique), name, created_at, updated_at, deleted_at (soft delete).
  - `tenant_memberships`: id, tenant_id, user_id, role, created_at.
  - `invitations`: id, tenant_id, email, inviter_user_id, token, status, expires_at.
- Existing domain tables: add `tenant_id UUID NOT NULL` + index (and unique composite indexes where necessary, e.g., `(tenant_id, name)`).
- Global tables: auth providers, feature flags (if any) remain tenant‑less.

Repository note
- Define global user model in the auth stack; tenant memberships determine per‑tenant roles.

## RLS Policies (Pattern)
- Enable RLS per tenant table: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`
- Policy pattern:
  - SELECT/UPDATE/DELETE: `USING (tenant_id = current_setting('app.tenant_id')::uuid AND deleted_at IS NULL)` (omit `deleted_at` where not present)
  - INSERT: `WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid)`
- Optional soft delete is encouraged for safer tenant deletion and recovery.

## Request Flow (MVP)
1. Request enters FastAPI.
2. Middleware resolves tenant from subdomain or `/:tenant` path.
3. Middleware stores tenant context on request state and configures the DB session with `SET LOCAL app.tenant_id`.
4. SQLAlchemy queries execute normally; RLS guarantees isolation.
5. Handlers and services do not need to manually filter by tenant ID (defense in depth: can still add `with_loader_criteria`).



## Frontend Considerations (Astro + Vue)
- Read current tenant from subdomain or `/:tenant` prefix using a `useTenant()` composable.
- Display a simple organization switcher in the navbar.
- API calls: do not rely on client to enforce tenancy. The backend resolves the tenant; clients may include a non‑authoritative header for ergonomics.



## Operational Decisions (MVP)
- Admin routes: Admin endpoints that manage tenant data (settings, follow-ups, API keys) are tenant‑scoped and must run with a resolved tenant; global admin operations remain explicit and separate.
- Rate limiting: MVP keeps global rate limits (identifier + type). Schema allows optional `tenant_id` for future per‑tenant limits.
- Security events: Prefer tenant‑scoped; allow `tenant_id` NULL for infra‑level events. Queries must handle both.
- Soft delete: Adopt `deleted_at` for key tenant tables (`admin_settings`, `followup_categories`, `followup_questions`, `welcome_questions`, `api_keys`). Optional for log-like tables.
- SQLAlchemy adoption: Introduce Engine/Session and per‑request transaction in M2; rely on RLS even if some routes continue with SQL text.

## Dev & Test Strategy
- Seed two tenants and cross‑check that cross‑tenant reads/writes are blocked by RLS.
- Pytest integration tests attempt cross‑tenant access and expect 403/empty results.
- Include `tenant_id` in logs for traceability.



## Non‑Goals (MVP)
- Billing, pricing plans, or metering.
- Custom domains per tenant (can come later).
- SSO/SCIM; basic email invitation flow only.

## Additional Documentation

### Implementation Resources
- **Code Examples**: `docs/multi_tenant/implementation_code.md` - Ready-to-use middleware, routes, and components
- **Configuration**: `docs/multi_tenant/config_templates.md` - Environment files, Docker configs, Railway setup
- **Testing**: `docs/multi_tenant/test_specifications.md` - RLS tests, integration tests, fixtures

### Operations Resources
- **Deployment**: `docs/multi_tenant/operations_guide.md` - Railway deployment, monitoring, backups
- **Migration**: `docs/multi_tenant/migration_guide.md` - SQLite to Postgres migration scripts and validation

## Risks & Mitigations
- App code accidentally bypasses scoping: rely on RLS as primary control; add `with_loader_criteria` in ORM for defense in depth.
- Long‑lived connections losing `SET LOCAL`: bind per‑request sessions; ensure middleware configures every transaction boundary.
- Unique constraints shifting: convert to composite uniques `(tenant_id, ...)` to avoid global collisions.
- Performance: index `tenant_id`; consider partial indexes where appropriate; monitor slow queries.

## Glossary
- Tenant: An organization that owns data and memberships.
- RLS: Row‑Level Security in Postgres enforcing per‑row access.
- `SET LOCAL app.tenant_id`: Per‑transaction variable used by RLS policies.
- Path fallback: Using `/:tenant` in URLs when subdomains are unavailable.

## ERD (Mermaid)
```mermaid
erDiagram
    TENANTS ||--o{ TENANT_MEMBERSHIPS : has
    TENANTS ||--o{ INVITATIONS : has
    USERS ||--o{ TENANT_MEMBERSHIPS : joins

    TENANTS ||--o{ ADMIN_SETTINGS : scopes
    TENANTS ||--o{ FOLLOWUP_CATEGORIES : scopes
    FOLLOWUP_CATEGORIES ||--o{ FOLLOWUP_QUESTIONS : contains
    TENANTS ||--o{ WELCOME_QUESTIONS : scopes
    TENANTS ||--o{ API_KEYS : scopes
    TENANTS ||--o{ QUERY_LOGS : scopes
    TENANTS ||--o{ CONTENT_GAPS : scopes
    TENANTS ||--o{ SECURITY_EVENTS : scopes

    TENANTS {
        uuid id PK
        string slug UNIQUE
        string name
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    USERS {
        bigint id PK
        string username UNIQUE
        string email UNIQUE
        string password_hash
        string role  // global role if any
        bool is_active
    }

    TENANT_MEMBERSHIPS {
        bigint id PK
        uuid tenant_id FK
        bigint user_id FK
        string role  // owner|admin|member
        timestamptz created_at
        UNIQUE (tenant_id, user_id)
    }

    INVITATIONS {
        bigint id PK
        uuid tenant_id FK
        string email
        bigint inviter_user_id FK
        string token UNIQUE
        string status  // pending|accepted|revoked
        timestamptz expires_at
        timestamptz created_at
    }

    ADMIN_SETTINGS {
        bigint id PK
        uuid tenant_id FK
        string setting_key
        text setting_value
        timestamptz updated_at
        UNIQUE (tenant_id, setting_key)
    }

    FOLLOWUP_CATEGORIES {
        bigint id PK
        uuid tenant_id FK
        string name
        string display_name
        text description
        string icon
        int sort_order
        bool is_active
        UNIQUE (tenant_id, name)
    }

    FOLLOWUP_QUESTIONS {
        bigint id PK
        uuid tenant_id FK
        bigint category_id FK
        text question_text
        int sort_order
        bool is_active
    }

    WELCOME_QUESTIONS {
        bigint id PK
        uuid tenant_id FK
        text question_text
        int sort_order
        bool is_active
    }

    API_KEYS {
        bigint id PK
        uuid tenant_id FK
        string key_name
        string key_type
        text encrypted_value
        string last_four
        bool is_active
        timestamptz last_used_at
        timestamptz last_validated_at
        UNIQUE (tenant_id, key_name)
    }

    QUERY_LOGS {
        bigint id PK
        uuid tenant_id FK
        text user_query
        text system_response
        string query_type
        float response_time_ms
        string llm_provider
        string llm_model
        float vector_search_score
        text sources_used
        text follow_up_questions
        bool cache_hit
        bool error_occurred
        text error_message
        text client_ip
        timestamptz timestamp
        index (tenant_id, timestamp)
    }

    CONTENT_GAPS {
        bigint id PK
        uuid tenant_id FK
        text query_pattern
        int occurrence_count
        float avg_similarity_score
        timestamptz first_seen
        timestamptz last_seen
        bool resolved
        text notes
        bigint sample_query_id FK
    }

    SECURITY_EVENTS {
        bigint id PK
        uuid tenant_id FK  // nullable if infra-level
        string event_type
        string identifier
        text details
        string severity
        text ip_address
        text user_agent
        timestamptz created_at
    }
```
