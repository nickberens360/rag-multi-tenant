# Multi‑Tenant Implementation — Progress Tracker

This document tracks progress against the greenfield multi‑tenant plan and the Agent Playbook tasks.

Last updated: 2025-09-28

## Status Summary
- Backend migration scaffolded (Alembic + RLS) — done
- Tenant middleware and per‑request session — done
- Tenant APIs (tenants, memberships, invitations) — done (MVP)
- Frontend tenant awareness (composable + switcher) — partial
- Frontend tenant pages (/:tenant) — pending (this change adds initial page)
- Observability (tenant_id in logs) — done (contextvars + logger)
- Tests (RLS + tenant resolution) — initial added; expand later
- Debug endpoint /api/debug/tenant — added (dev-only)
- Stats/Performance now PG-only (SQLite fallback removed)
- Queries and Content gaps now PG-only (RLS scoped)
- Tenant slug→id caching added in middleware (in-memory TTL)
- Query logger switched to Postgres (RLS-aware) for all write paths
- Follow-up categories/questions and welcome questions migrated to Postgres APIs
- SQLite query logger removed; remaining SQLite utilities slated for deprecation
- Admin users/sessions routes migrated to Postgres
- Taxonomy settings now read/write from Postgres `admin_settings`; history snapshots in `taxonomy_settings_history`
- Rate limiting moved to Postgres table `rate_limiting`; admin auth now reads/writes attempts in PG
 - 2FA (user_2fa) migrated to Postgres; TOTP service uses PG + audit logger
 - Settings helpers: SettingsManager now uses Postgres for all reads/writes; taxonomy_loader reads from PG
 - **[2025-09-28] Multi-tenant hardening completed**:
   - Added explicit tenant filters to all followup category/question read queries (already in place)
   - Fixed 5 taxonomy_settings_history queries missing tenant filters
   - Added tenant-change watchers to all 6 admin settings views (Core, Knowledge, Taxonomy, Response, Security, Features)

## Playbook Tasks

1. p1_env_alembic — Configure env + Alembic
   - Files: .env, .env.example, backend/db/alembic.ini, backend/db/env.py
   - Status: Completed

2. p1_initial_schema — Initial schema + RLS
   - Files: backend/db/versions/init_multi_tenant_schema.py
   - Status: Completed

3. p2_backend_middleware — Tenant middleware
   - Files: backend/core/tenant_middleware.py, backend/core/app_factory.py
   - Status: Completed

4. p2_backend_session — SQLAlchemy engine + per‑request session
   - Files: backend/core/db_session.py, backend/main.py
   - Status: Completed (RLS variable set only if ENABLE_RLS_ENFORCEMENT=true)

5. p2_tenant_apis — Tenants/memberships/invitations endpoints
   - Files: backend/routes/tenants.py, backend/routes/invitations.py
   - Status: Completed (MVP; service layer optional)

6. p3_frontend — Tenant awareness + org switcher
   - Files: src/composables/useTenant.ts, src/components/OrgSwitcher.vue, src/pages/[tenant]/index.astro
   - Status: Partial (index page added; no shared layout wiring by design)

7. p3_observability_tests — Observability + tests
   - Files: backend/core/audit_logger.py, tests/integration/test_tenancy_rls.py, tests/integration/test_tenant_resolution.py
   - Status: In Progress (tenant_id logging + tests being added)

## Open Items
- Enable RLS enforcement in environments that use Postgres‑backed routes: set `ENABLE_RLS_ENFORCEMENT=true`.
- Decommission remaining SQLite helpers (database_utils, query_data_manager) — done; knowledge_index_db migrated to Postgres
- Admin UI: optionally read /api/debug/tenant when no membership found.

## Next Actions
- [x] Migrate admin users and sessions to Postgres schema (add tables + routes), then drop admin_database
  - Ported endpoints: /auth/me, /auth/change-password, /users (list/create/delete/reactivate/deactivate/bulk ops), /security/session-stats, health check
  - Routes now query admin_users/admin_sessions via SQLAlchemy Session; auditing writes to security_events
  - Added display_name column via Alembic; /user/display-name now updates Postgres
- [x] Persist audit logger to Postgres `security_events` for admin auth flows (login/password/session events)
 - [x] Migrate 2FA storage to PG (user_2fa) and switch to audit logger
 - [x] Remove admin_database (all references dropped)
- [x] **Multi-tenant hardening (2025-09-28)**:
  - Added explicit tenant filters to prevent data leakage with superuser sessions
  - Fixed taxonomy_settings_history queries missing tenant isolation
  - Implemented frontend reactivity for all settings views on tenant switch
- [ ] Expand PG integration tests for follow-up/welcome APIs (auth overrides added)
- [ ] Add PG tests for taxonomy settings and versioning (create/update/list/restore)
- [x] Add PG tests for admin auth basics and rate limiting
- [ ] Add PG tests for 2FA flows (enable/verify/disable)
