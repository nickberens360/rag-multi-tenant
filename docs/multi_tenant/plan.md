# Multi‑Tenant Greenfield Plan

Status (as of 2025-09-24)

- New codebase copy with no need for SQLite migration, rollbacks, or cutover.
- Implement Postgres + SQLAlchemy + RLS from day one; multi‑tenant paths are the default.

Agent quick links
- Agent Playbook (guide): `docs/multi_tenant/agent_playbook.md`
- Machine-readable index: `docs/multi_tenant/agent_playbook.yaml` (JSON: `docs/multi_tenant/agent_playbook.json`)

Assumptions
- Database: Postgres 14+. ORM: SQLAlchemy (Core or ORM). API: FastAPI. Frontend: Astro + Vue.
- Tests: pytest (backend), Vitest (frontend). App role is `NOBYPASSRLS`.

Phases

Phase 1 — Schema + RLS (Initial Revision)
- Create all tables including `tenants`, `tenant_memberships`, `invitations`, and tenant‑scoped domain tables with `tenant_id UUID NOT NULL`.
- Define composite uniques that include `tenant_id` (e.g., `UNIQUE(tenant_id, name)`).
- Enable RLS and policies on tenant tables; optional `FORCE ROW LEVEL SECURITY`.
- Seed default tenant (`DEFAULT_TENANT_ID`).

Acceptance
- `alembic upgrade head` creates schema and policies without errors.
- `SET LOCAL app.tenant_id = :tid` filters rows by tenant as expected in psql.

Phase 2 — Backend Wiring + Tenant APIs
- Tenant middleware: resolve tenant (subdomain > `/:tenant`), set `request.state.tenant_id`.
- SQLAlchemy engine + per‑request session dependency; begin a transaction; execute `SET LOCAL app.tenant_id = :tid` on every request.
- Implement tenant CRUD, memberships, and invitation endpoints.

Acceptance
- Requests operate under tenant context with no per‑query filters required (RLS enforces isolation).
- Cross‑tenant access returns 403 or empty per route semantics.

Phase 3 — Frontend + Observability
- `useTenant()` composable to parse subdomain or `/:tenant` prefix; org switcher component.
- Include `tenant_id` in structured logs and request IDs; basic per‑tenant counters.
- Add integration tests for tenant switching and RLS behavior.

Acceptance
- UI switches tenants and data isolates accordingly.
- Logs/metrics filter by `tenant_id`; RLS integration tests pass.

Out of Scope (initial)
- Billing/SSO/SCIM; custom domains; per‑tenant data export/import.

Notes
- Prefer SQLAlchemy Core initially to minimize complexity; add ORM models and `with_loader_criteria` as defense‑in‑depth later.
- Design all new uniques as composite with `tenant_id` to avoid collisions.
