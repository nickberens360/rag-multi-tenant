# Agent Playbook — Multi‑Tenant Implementation (Greenfield)

Purpose
- Provide an agent‑oriented, machine‑parsable plan to implement multi‑tenancy in a straight‑line greenfield path.
- Build directly on Postgres + SQLAlchemy + RLS using explicit files, commands, and validation steps.

Greenfield assumptions
- New codebase copy; no SQLite migration or cutover required.
- Postgres is the primary database from day one.

Machine‑Readable Task Index (YAML)

```yaml
version: 2
context:
  mode: greenfield
  db: postgres
  orm: sqlalchemy_core_or_orm
  rls: true
  tenancy: subdomain_or_path_prefix

tasks:
  - id: p1_env_alembic
    title: Configure env + Alembic
    depends_on: []
    files_to_touch: [".env", ".env.example", "backend/db/alembic.ini", "backend/db/env.py"]
    add_env:
      - { key: DATABASE_URL, example: postgresql+psycopg://user:password@localhost:5432/appdb }
      - { key: DEFAULT_TENANT_ID, example: 00000000-0000-0000-0000-000000000001 }
    validation:
      - { command: psql "$DATABASE_URL" -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" }

  - id: p1_initial_schema
    title: Initial schema + RLS (single revision)
    depends_on: [p1_env_alembic]
    files_to_touch:
      - backend/db/versions/init_multi_tenant_schema.py
    validation:
      - { command: alembic upgrade head }
      - { command: psql "$DATABASE_URL" -c "SET LOCAL app.tenant_id = '$DEFAULT_TENANT_ID'; SELECT COUNT(*) FROM tenants;" }

  - id: p2_backend_middleware
    title: Tenant middleware (subdomain > path prefix)
    depends_on: [p1_initial_schema]
    files_to_touch:
      - backend/core/tenant_middleware.py
      - backend/core/app_factory.py
    validation:
      - { description: request.state.tenant_id resolves from host/path }

  - id: p2_backend_session
    title: SQLAlchemy engine + per-request session (SET LOCAL)
    depends_on: [p2_backend_middleware]
    files_to_touch:
      - backend/core/db.py
      - backend/core/db_session.py
      - backend/main.py
    validation:
      - { description: Every request starts a transaction and sets app.tenant_id }

  - id: p2_tenant_apis
    title: Tenants/memberships/invitations endpoints (MVP)
    depends_on: [p2_backend_session]
    files_to_touch:
      - backend/routes/tenants.py
      - backend/routes/invitations.py
      - backend/core/membership_service.py
    validation:
      - { description: Create tenant, add member, list user tenants; accept invite }

  - id: p3_frontend
    title: Frontend tenant awareness + org switcher
    depends_on: [p2_tenant_apis]
    files_to_touch:
      - src/composables/useTenant.ts
      - src/components/OrgSwitcher.vue
      - src/pages/[tenant]/index.astro
    validation:
      - { description: Switching tenants changes data context }

  - id: p3_observability_tests
    title: Observability + RLS and routing tests
    depends_on: [p2_backend_session]
    files_to_touch:
      - backend/core/audit_logger.py
      - tests/integration/test_tenancy_rls.py
      - tests/integration/test_tenant_resolution.py
    validation:
      - { description: Logs include tenant_id; integration tests pass }
```

Anchors and Search Hints
- Tenancy middleware insertion (backend/core/app_factory.py)
  - search_hint: `rg -n "add_security_middleware|configure_cors|include_router\(" backend/core/app_factory.py`
  - insertion_hint: Add `app.middleware("http")(tenant_middleware)` after security middleware and before router registrations.

- Per-request session dependency (backend/core/db_session.py)
  - search_hint: `rg -n "lifespan\(|create_app\(|FastAPI\(" backend`
  - insertion_hint: Define `get_db_session(request)` dependency; in routes using Postgres, add `Depends(get_db_session)`.

- Backend entry (backend/main.py)
  - search_hint: `rg -n "lifespan|create_app\(|app = create_app" backend/main.py`
  - insertion_hint: If needed, initialize DB engine on startup; keep logic minimal in main and prefer core modules.

- Tenant routers (backend/core/app_factory.py)
  - search_hint: `rg -n "include_router\(" backend/core/app_factory.py`
  - insertion_hint: Register `tenants` and `invitations` routers under `/api/admin` (or `/api`) as appropriate.

Minimal API Specs (for scaffolding later)
- Tenants
  - POST `/api/admin/tenants` → { id, slug, name }
  - GET `/api/admin/tenants/mine` → [ { id, slug, role } ]
- Memberships
  - POST `/api/admin/tenants/{tenant_id}/members` → add member (role required)
  - DELETE `/api/admin/tenants/{tenant_id}/members/{user_id}`
- Invitations
  - POST `/api/admin/invitations` → { token, tenant_id, expires_at }
  - POST `/api/admin/invitations/accept` → { tenant_id, status }

Test Contracts (to add when implementing)
- Backend (pytest)
  - `tests/integration/test_tenancy_rls.py` — verifies cross‑tenant reads/writes blocked once RLS is on.
  - `tests/integration/test_tenant_resolution.py` — subdomain vs `/:tenant` resolution precedence.
  - `tests/unit/test_tenant_memberships.py` — role checks on membership changes.
- Frontend (Vitest)
  - `src/composables/useTenant.test.ts` — parsing subdomain/route and reactive updates.
  - `src/components/OrgSwitcher.test.ts` — switching tenant updates route and fetch base.

Notes for Agents
- Always start a transaction and execute `SET LOCAL app.tenant_id = :tid` per request.
- Do not trust client headers for tenant security; resolution must be server‑side.
- Design uniques as `(tenant_id, ...)` from the start to prevent collisions.

References
- Overview: `docs/multi_tenant/overview.md`
- Plan: `docs/multi_tenant/plan.md`
- Initial schema: `docs/multi_tenant/migrations_outline.md`
