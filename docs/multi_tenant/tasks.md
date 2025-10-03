# Multi‑Tenant Tasks (Greenfield)

This is the actionable task list to deliver the Multi‑Tenant MVP in a fresh codebase. It aligns with the greenfield plan and initial schema outline.

Agent quick links
- Agent Playbook (guide): `docs/multi_tenant/agent_playbook.md`
- Machine-readable index: `docs/multi_tenant/agent_playbook.yaml` (JSON: `docs/multi_tenant/agent_playbook.json`)

Scope
- In scope (MVP): shared‑schema Postgres, `tenant_id` scoping + RLS, tenant resolution middleware, minimal org switcher, basic invitations, observability.
- Out of scope: billing/SSO/custom domains/SCIM, hard multi‑db sharding.

Legend
- [ ] Todo
- [~] In Progress
- [x] Done

Phase Summary
- P1: Initial schema + RLS (single revision)
- P2: Backend wiring (middleware + session) + Tenant APIs
- P3: Frontend tenant awareness + Observability and tests

---

P1 — Initial Schema + RLS

- [ ] Configure env and Alembic
  - Acceptance: `psql` connects; `pgcrypto` extension exists
- [ ] Create initial schema with tenants/memberships/invitations and tenant‑scoped domain tables
  - Acceptance: `alembic upgrade head` completes; tables exist with composite uniques
- [ ] Enable RLS policies on tenant‑scoped tables
  - Acceptance: `SET LOCAL app.tenant_id` filters data in psql
- [ ] Seed default tenant
  - Acceptance: Default tenant present

---

P2 — Backend Wiring + Tenant APIs

- [ ] Tenant middleware (subdomain > `/:tenant`)
  - Acceptance: `request.state.tenant_id` set for all requests
- [ ] SQLAlchemy engine + per‑request session (transaction + `SET LOCAL app.tenant_id`)
  - Acceptance: Every request sets `app.tenant_id`; RLS enforced
- [ ] Tenants + memberships + invitations endpoints
  - Acceptance: Create tenant, add/remove member, list user’s tenants, invite + accept

---

P3 — Frontend + Observability

- [ ] `useTenant()` composable and minimal org switcher
  - Acceptance: Switching updates route/context; no reload required
- [ ] Observability (logs/metrics include `tenant_id`)
  - Acceptance: Logs filterable by `tenant_id`; basic counters present
- [ ] Integration tests for routing + RLS
  - Acceptance: Cross‑tenant attempts fail; same‑tenant succeed

---

References
- Overview: `docs/multi_tenant/overview.md`
- Plan: `docs/multi_tenant/plan.md`
- Initial schema: `docs/multi_tenant/migrations_outline.md`
