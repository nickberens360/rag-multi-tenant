# API Routing Standardization Plan

Owner: Backend/Platform
Status: Draft (proposed)
Scope: Public + Admin HTTP API paths (FastAPI), Astro dev proxy, docs

## Summary

We currently expose a mix of root-level endpoints (e.g., `/`, `/status`, `/query`) and `/api/public`-prefixed routes, while admin routes live under `/api/admin`. This inconsistency complicates client usage, proxying, observability, and documentation. This plan standardizes all public API endpoints under a single `/api` prefix (keeping temporary aliases for compatibility) and corrects the docs to match the actual paths.

## Current State (as of repo HEAD)

Implemented via `backend/core/app_factory.py` includes:
- Root-level (no prefix):
  - Health: `GET /`, `GET /status`, `GET /health`, `GET /rate-limits`, `GET /db-paths`, `GET /welcome-questions` (from `backend/routes/health.py`)
  - Query: `POST /query`, `GET /default-model` (from `backend/routes/query.py`)
- Public API (prefixed):
  - Mounted at `/api/public`: `smart_query.py` (`/smart-query`, `/smart-query/status`, `/smart-query/analyze`),
    `knowledge_public.py` (`/knowledge/...`), plus `content.py`, `stats.py`, `performance.py` endpoints.
- Admin API (prefixed):
  - Mounted at `/api/admin`: authentication, analytics, queries, knowledge admin, etc.

Docs mismatches noted in `CLAUDE.md`:
- Smart Query listed as `/api/smart-query` but code serves `/api/public/smart-query`.
- Admin endpoints documented as `/admin/api/...` but code serves `/api/admin/...`.

## Goals

- Single, consistent public base path: `/api`.
- Keep admin under `/api/admin` (unchanged), fix docs where they diverge.
- Preserve root health checks for load balancers (`/` and `/health`) as temporary aliases.
- Enable easy versioning later (`/api/v1`) without breaking clients again.

## Proposed Target Topology

- Public (no auth):
  - Health/Status: `GET /api/` (alias of `/api/health`), `GET /api/health`, `GET /api/status`, `GET /api/rate-limits`, `GET /api/db-paths`, `GET /api/welcome-questions`
  - Query: `POST /api/query`, `GET /api/default-model`
  - Smart Query (advanced): `POST /api/smart-query`, `GET /api/smart-query/status`, `POST /api/smart-query/analyze`
  - Knowledge (read-only): `GET /api/knowledge/...`
- Admin (auth): `...` under `/api/admin/...` (unchanged)
- Temporary aliases for compatibility:
  - Keep existing root routes (`/`, `/status`, `/health`, `/rate-limits`, `/db-paths`, `/welcome-questions`, `/query`, `/default-model`) for one deprecation cycle.
  - Optionally keep `/api/public/...` aliases pointing to the same handlers for one cycle.

## Implementation Plan

1) FastAPI routing changes
- File: `backend/core/app_factory.py`
  - Add a grouped include for public routers with `prefix="/api"`:
    - `app.include_router(health.router, prefix="/api")`
    - `app.include_router(query.router, prefix="/api")`
    - Change existing public includes from `prefix="/api/public"` to `prefix="/api"` for `smart_query`, `content`, `stats`, `performance`, `knowledge_public`.
  - Keep existing root-level includes for health and query temporarily to avoid breaking clients during rollout.
  - Optionally, to avoid double OpenAPI entries, include the routers only once for docs but register lightweight alias routes that call the same functions (nice-to-have; not required for first pass).

2) Astro dev proxy (DX and CORS simplification)
- File: `astro.config.mjs`
  - Add a dev proxy so the frontend can call `/api` without CORS issues:
    ```js
    export default defineConfig({
      // ...existing config
      server: {
        proxy: {
          '/api': 'http://localhost:8000'
        }
      }
    })
    ```
  - Confirm production reverse proxy (Netlify/Vercel/NGINX) forwards `/api/*` to FastAPI.

3) Documentation updates
- File: `CLAUDE.md`
  - Update Public Endpoints to show `/api/...` paths.
  - Correct Admin endpoints to `/api/admin/...` (not `/admin/api/...`).
  - Add a Deprecation Note: root endpoints and `/api/public` are deprecated and will be removed in Release N+2.

4) Frontend updates (if any)
- Search/replace any client calls to root endpoints or `/api/public` and update them to `/api` (none found under `src/` and `admin/frontend/src/` currently, but re-check post-merge).
- If consumers exist outside the repo, announce the change with a timeline (see Rollout).

5) Observability and Monitoring
- Ensure logs/metrics/alerts use `/api/*` paths.
- Update any dashboards or API monitors pinging `/status` to use `/api/status` (keep `/status` alias active during deprecation).

## Backwards Compatibility & Deprecation

- Release N (this change):
  - Serve all public endpoints under `/api/*`.
  - Keep root-level routes and `/api/public` as working aliases.
  - Emit `Deprecation` header on alias routes when feasible.
- Release N+1:
  - Keep aliases; add warning logs and update external consumers.
- Release N+2:
  - Remove root-level public routes and `/api/public`.
  - Keep `/` root health optional if infra requires it; otherwise remove.

## Risks & Mitigations

- Client breakage: Mitigated by temporary aliases and clear docs.
- OpenAPI duplication: Can occur if routers are included twice. Short-term acceptable; longer-term we can add hidden alias endpoints or manual docs tweaks.
- Maintenance middleware assumptions: Current checks skip `/api/admin` and `/admin`—remains valid; public move to `/api` is unaffected.
- Load balancers expecting `/` or `/health`: Keep aliases at root through deprecation; optionally retain `/health` indefinitely.

## Validation Checklist

- Smoke test endpoints:
  - `GET /api/health`, `/api/status`, `/api/rate-limits`
  - `POST /api/query` (streaming and headers)
  - `GET /api/default-model`
  - `POST /api/smart-query`, `GET /api/smart-query/status`, `POST /api/smart-query/analyze`
  - `GET /api/knowledge/documents`, `/api/knowledge/stats`, `/api/knowledge/sources`
- Verify root aliases still function during rollout.
- OpenAPI schema reflects `/api/*` and no broken tags.
- Astro dev proxy forwards `/api` → FastAPI `:8000`.
- CORS still passes (or becomes moot with proxy).

## Effort Estimate

- Code changes: ~30–60 minutes (app_factory includes + quick smoke checks).
- Docs + config: ~30 minutes.
- Rollout comms/tests: depends on external consumers.

## Appendix: Key Files

- Backend routing: `backend/core/app_factory.py`, `backend/routes/*.py`
- Frontend dev proxy: `astro.config.mjs`
- Docs: `CLAUDE.md` (update paths), this plan file

