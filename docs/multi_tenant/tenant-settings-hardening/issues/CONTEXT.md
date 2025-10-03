# Context: Multi‑Tenant Hardening

Goal: ensure all admin and public data access is correctly scoped to the active tenant, and that the admin UI refreshes when the organization (tenant) changes.

Key principles
- Backend: always set `app.tenant_id` on the DB session (and transaction) and reset it on teardown
- Backend: add explicit `WHERE tenant_id = <current tenant>` to SELECTs on tenant‑scoped tables (in addition to RLS)
- Frontend: use a tenant‑prefixed router (`/:tenant/...`), and reload data on `tenant` change; keep Axios base pointing at `/{tenant}/api/admin`

Already fixed (high level)
- DB session now sets and resets `app.tenant_id` (with fallback)
- Audit logging serializes UUIDs and attaches tenant context
- Admin and public welcome questions endpoints explicitly filter by tenant
- Tenant‑prefixed admin routes mounted (including knowledge endpoints)
- Router uses `/:tenant`, and `/` redirects to first available tenant
- Frontend Axios base includes `/{tenant}/api/admin`; several views (UX, Welcome, Knowledge Sources) and follow‑up components reload on org switch

Remaining work (high level)
- Add explicit tenant filters to settings reads (admin_settings and related history reads)
- Add explicit tenant filters to follow‑up list endpoints (categories, questions, stats)
- Ensure the remaining settings views reload on tenant change (Core, Knowledge, Taxonomy, Response, Security, Features)

