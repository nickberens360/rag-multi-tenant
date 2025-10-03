# Domain Table Inventory — Tenant Scoping and Uniques

This document enumerates current data tables in the project and specifies which ones become tenant‑scoped (add `tenant_id`) vs. remain global. It also lists unique constraints that must be converted to composite tenant‑scoped uniques in the Postgres multi‑tenant MVP.

Current storage uses multiple SQLite databases; target is a unified Postgres DB with RLS. Mapping and scoping below reflect that target.

Greenfield mode
- Create tenant‑scoped tables from day one (include `tenant_id` in schema and uniques). The SQLite mapping in this document is historical context only.

Repository status notes (as of 2025-09-23)
- The backend currently uses SQLite only; Postgres and RLS are not wired.
- Admin data live in `admin_monitoring.db` via `AdminDatabaseManager` (see `backend/core/admin_database.py`).
- Query analytics live in `rag_monitoring.db` via `SQLiteQueryLogger` (see `backend/core/sqlite_query_logger.py`).
- Security events exist both in admin DB and, in places, a dedicated `security_events.db` via `SecurityEventsDatabaseManager`.
- `admin_users` maps to target `users`; `admin_sessions` maps to target `sessions` (global).

## Storage Landscape (Current → Target)
- Admin DB (SQLite: `admin_monitoring.db`) → Postgres schema `public`
- Query Analytics DB (SQLite: `rag_monitoring.db`) → Postgres schema `public`
- Security Events DB (SQLite: `security_events.db`) → Postgres schema `public`

New global tables in target:
- `tenants` (global)
- `tenant_memberships` (global; links users↔tenants)
- `invitations` (global; per‑tenant invites)
- `users` (global; replaces `admin_users` semantics)

## Table Scoping and Unique Changes

Legend
- Scope: tenant = add `tenant_id UUID NOT NULL`; global = no `tenant_id`.
- Unique changes: convert global uniques to composite with `tenant_id`.

### Admin DB Tables

- admin_users
  - Scope: global (becomes `users`).
  - Current uniques: `username` UNIQUE; consider adding `email` UNIQUE in target.
  - Notes: user accounts are global across tenants; roles per tenant via memberships.

- admin_sessions
  - Scope: contextual; keep global but store `current_tenant_id` nullable for UX.
  - Uniques: none.
  - Notes: sessions remain per user; selected tenant stored in session/JWT claim.

- admin_settings
  - Scope: tenant.
  - Unique changes: `setting_key` UNIQUE → composite UNIQUE (`tenant_id`, `setting_key`).
  - Current repo: table is global (SQLite) with unique `setting_key`.

- taxonomy_settings_history
  - Scope: tenant.
  - Unique changes: none.
  - Current repo: table exists in SQLite for history snapshots; will be tenant‑scoped post‑migration.

- rate_limiting
  - Scope: global with optional tenant dimension.
  - Uniques: UNIQUE (`identifier`, `identifier_type`) → optionally (`tenant_id`, `identifier`, `identifier_type`) if rate limits should be per tenant.
  - Notes: can remain global; add nullable `tenant_id` for future filtering.

- security_events (admin DB copy)
  - Scope: tenant (preferred) or global if events are infrastructure‑level.
  - Uniques: none.
  - Notes: duplicate table also exists in dedicated Security DB; in target, use a single `security_events` table.
  - Current repo: both patterns exist; consolidate during migration.

- user_2fa
  - Scope: global (per user).
  - Uniques: UNIQUE (`user_id`) unchanged.

- followup_categories
  - Scope: tenant.
  - Unique changes: `name` UNIQUE → composite UNIQUE (`tenant_id`, `name`).

- followup_questions
  - Scope: tenant.
  - Uniques: none (PK only). Consider FK to `followup_categories(id)` with matching tenant.

- welcome_questions
  - Scope: tenant.
  - Uniques: none (PK only).

- api_keys
  - Scope: tenant (per‑tenant provider configuration).
  - Unique changes: `key_name` UNIQUE → composite UNIQUE (`tenant_id`, `key_name`).

### Query Analytics DB Tables

- query_logs
  - Scope: tenant.
  - Uniques: none.
  - Indexes: add `INDEX (tenant_id)`, and consider composite indexes on common filters (e.g., `(tenant_id, timestamp DESC)`).

- content_gaps
  - Scope: tenant.
  - Uniques: none.
  - FKs: `sample_query_id` → `query_logs(id)`; ensure both rows share the same `tenant_id` via `WITH CHECK` policy.

### Security Events DB Tables

- security_events
  - Scope: tenant preferred; some events may be global.
  - Uniques: none.
  - Notes: In target, consolidate into the single `security_events` table with `tenant_id` nullable when event is not tied to a tenant.

## New Tables (Target)

- tenants (global)
  - Columns: `id UUID PK`, `slug UNIQUE`, `name`, timestamps, `deleted_at`.

- tenant_memberships (global)
  - Columns: `id`, `tenant_id UUID FK`, `user_id FK`, `role`, timestamps.
  - Unique: composite UNIQUE (`tenant_id`, `user_id`).

- invitations (global)
  - Columns: `id`, `tenant_id FK`, `email`, `inviter_user_id FK`, `token`, `status`, `expires_at`, timestamps.
  - Unique: `token` UNIQUE (global) is acceptable.

## Backfill and RLS Policy Considerations

- Add `tenant_id` as NULLable first, backfill, then set NOT NULL to avoid table rewrites.
- Convert uniques in this order: drop old unique, add composite unique.
- Apply RLS per tenant table with pattern:
  - USING: `tenant_id = current_setting('app.tenant_id')::uuid AND (deleted_at IS NULL OR deleted_at IS NULL)`
  - WITH CHECK: `tenant_id = current_setting('app.tenant_id')::uuid`
- Ensure referential integrity across tenant‑scoped relations (e.g., `followup_questions.category_id` belongs to same `tenant_id`).

## Inventory Summary (Checklist)

Tenant‑scoped (add `tenant_id`)
- admin_settings → UNIQUE (`tenant_id`, `setting_key`)
- taxonomy_settings_history (index `tenant_id`)
- followup_categories → UNIQUE (`tenant_id`, `name`)
- followup_questions (FK → category; index `tenant_id`)
- welcome_questions (index `tenant_id`)
- api_keys → UNIQUE (`tenant_id`, `key_name`)
- query_logs (index `tenant_id`, `(tenant_id, timestamp)`)
- content_gaps (index `tenant_id`; FK sample_query_id constrained to same tenant)
- security_events (preferred: add `tenant_id` nullable; index it)
- rate_limiting (optional: add nullable `tenant_id`; composite UNIQUE if per‑tenant desired)

Global (no `tenant_id`)
- tenants, tenant_memberships, invitations
- users (replaces admin_users)
- user_2fa (per user)
- sessions (store `current_tenant_id` for context, but not enforced via RLS)

Open Decisions
- Whether admin_sessions should be replaced with a unified `sessions` table and include `current_tenant_id`.
- If rate limiting policies should be global or per tenant; schema supports both with nullable `tenant_id`.
- Whether security events are always tenant‑bound or sometimes global; schema allows nullable `tenant_id`.
