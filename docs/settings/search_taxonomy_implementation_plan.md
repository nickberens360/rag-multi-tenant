# Search & Taxonomy Settings – Implementation Plan (No Code Changes Yet)

This document outlines what it will take to fully implement the Admin “Search & Taxonomy” settings so they persist in SQLite and are consumed by backend logic. It captures current state, proposed data model, API, backend wiring, and testing/operational considerations.

- Scope: Admin UI `Search & Taxonomy` page (currently UI-only), FastAPI backend, SQLite admin DB.
- Goal: Let admins edit taxonomy (categories, synonyms, regex, router options) via UI; store persistently; apply to runtime detection and “content_type” classification, with a safe rollout and reindex path.

---

**Current State**
- Frontend UI exists at `admin/frontend/src/views/settings/TaxonomySettings.vue` with Monaco JSON editor; it saves drafts only to `localStorage` and runs client-side tests.
- Backend loads taxonomy from file: `backend/core/topic_taxonomy.json` via `backend/core/taxonomy_loader.get_topic_taxonomy()` with simple in‑process cache.
- Runtime consumers:
  - `backend/core/content_router.ContentRouter.detect_content_types()` uses taxonomy for query intent detection (synonyms/regex) and falls back to hardcoded heuristics.
  - `backend/core/startup_content_classifier.StartupContentClassifier` uses taxonomy to help assign metadata `content_type(s)` during indexing/refresh.
- Query Router ignore words are hardcoded in `backend/core/query_router.py` (not yet fed by taxonomy’s `router.ignore_words`).
- Admin DB already exists with a general `admin_settings` key/value table; many settings pages use it via `SettingsManager`.

---

**Proposed Data Model (SQLite)**
- Store Taxonomy as a single JSON blob in `admin_settings` table to minimize schema churn and match the UI’s JSON editor.
- Key: `taxonomy_settings` (new).
- Value: JSON with shape aligning to current file format:
  - version: string (e.g., "1")
  - categories: object keyed by category name → object with optional fields:
    - synonyms: string[]
    - regex: string[] (validated as compilable patterns)
    - metadata: object (e.g., { is_illustration_data: true })
    - routing: object (optional per-category routing hints like k, score_threshold)
  - router: object (optional), e.g. { ignore_words: string[] }

Rationale:
- Consistent with how other settings are persisted (simple JSON in `admin_settings`).
- Matches the existing file format so runtime consumers remain unchanged.
- Avoids immediate need for normalized tables (categories/synonyms/regex), which would complicate the UI and add migrations and joins without clear benefit.

Notes/Options:
- Optional future: introduce `taxonomy_settings_history` table for versioned backups; not required for initial implementation.

---

**Backend API**
Add two endpoints under the existing Admin router (`/api/admin`), mirroring other settings pages:
- GET `/settings/taxonomy` → returns `{ settings: <json> }`
- PUT `/settings/taxonomy` → accepts raw JSON of taxonomy; validates; writes to DB via `admin_db_manager.set_admin_setting('taxonomy_settings', ...)`, records `updated_by`, and returns `{ success, message, settings, lastUpdated }`.

Behavior & Validation:
- Auth: `require_admin_auth` dependency (like other settings endpoints).
- Audit: log via `audit_logger` with `CONFIG_UPDATE` and the resource `taxonomy_settings`.
- Rate Limit: same limiter pattern as other admin settings (if applied globally) is fine.
- Validation steps on PUT:
  - JSON must be an object with `categories` object.
  - Each category config: `synonyms` and `regex` must be arrays if present.
  - Compile each regex to ensure it is valid (reject bad patterns with 400).
  - Optional size guardrail: limit total JSON length (e.g., 256 KB) to prevent abuse.
  - Optional name constraints: category keys should be non-empty, lowercase alphanumeric + dashes/underscores.
- Cache invalidation: invalidate taxonomy cache (see “Loader & Caching” below) so subsequent requests pick up new config.

Seed & Defaults:
- If DB key is missing on GET, respond with the current file-based default (`backend/core/topic_taxonomy.json`), and do not write to DB. On first PUT, DB becomes the source of truth.
- Optional admin action: `POST /settings/taxonomy/reset` to restore file baseline into DB.

---

**Settings Manager Integration**
Extend `backend/core/settings_manager.py` and `SettingKeys` with `TAXONOMY_SETTINGS` to have a unified retrieval path:
- `get_taxonomy_settings()` returns the parsed JSON (dict) or default if not present.
- `set_taxonomy_settings(json_dict, updated_by)` writes to DB and invalidates cache.

Alternatively (minimal change set):
- Keep taxonomy separate from `SettingsManager` and update `taxonomy_loader` to read from DB via `admin_db_manager.get_admin_setting('taxonomy_settings')` when available. This is simpler and avoids expanding settings schemas.

Recommendation: start with the minimal approach (loader reads DB, falls back to file) to keep the change surface small and avoid schema classes for an open-ended JSON.

---

**Loader & Caching Changes**
Update `backend/core/taxonomy_loader.py`:
- On `get_topic_taxonomy(force_reload=False)`:
  1) If in‑process cache is valid and not `force_reload`, return cached.
  2) Try DB: fetch `taxonomy_settings` from `admin_settings`. If present, parse and validate structural shape (`categories` object). Cache and return.
  3) Fallback to file `topic_taxonomy.json` (current behavior).
- Add a small helper to clear cache or accept `force_reload=True` as a public way to bypass cache.
- Log source selection (DB vs file) for observability.

Cache Invalidation Triggers:
- After successful PUT, call `get_topic_taxonomy(force_reload=True)` to refresh cache.
- Optionally, add a simple `taxonomy_loader.invalidate_cache()` and call it from the route.

---

**Runtime Consumption**
- Intent Detection: `ContentRouter.detect_content_types` continues to call `get_topic_taxonomy()` and will automatically use DB-backed taxonomy once loader is updated. No consumer changes required.
- Startup Classification: `StartupContentClassifier` already calls `get_topic_taxonomy()`; reindexing should reflect new taxonomy in `content_type` metadata.
- Query Router Ignore Words: Currently hardcoded in `QueryRouter.ignore_words`. Optionally, extend `QueryRouter` to merge in `taxonomy.router.ignore_words` if present. This is a nice-to-have and can be a follow-up PR.

Reindexing:
- Changing taxonomy impacts classification tags stored as vector-store metadata. To fully apply changes, trigger a reindex.
- Use existing admin refresh endpoint: `POST /api/admin/refresh { force_reindex: true }` to set the `.refresh_required` flag consumed by `app_initializer_v2` on next startup. Document this in the UI flow.

Hot Reload vs. Restart:
- Intent detection (query-time) picks up new taxonomy immediately after cache invalidation — no restart needed.
- Content classification (startup-time) requires reindex; thus taxonomy updates should present an option to “Apply and reindex on restart.”

---

**Frontend Wiring (Admin UI)**
Update `admin/frontend/src/services/api.js` with new methods:
- `getTaxonomySettings()` → GET `/settings/taxonomy`
- `updateTaxonomySettings(json)` → PUT `/settings/taxonomy`
- Optional: `triggerRefresh(forceReindex=true)` → POST `/refresh`

Update `TaxonomySettings.vue` behavior:
- On mount: load taxonomy from API. If empty, populate from example (and show info banner that the example is not yet saved).
- Validate locally (existing “Validate JSON” button) before calling PUT.
- On save: call `updateTaxonomySettings`, show success toast; optionally offer to trigger refresh to reindex.
- Remove `localStorage` as the primary persistence; keep it only as an unsaved-draft autosave if desired, but the authoritative source must be DB.
- Display `lastUpdated` and possibly `updatedBy` from response for admin context.

---

**Validation & Security**
- Enforce payload size cap; reject oversized JSON with 413 or 400.
- Compile regex patterns on save; reject invalid ones with clear messages.
- Normalize category identifiers (e.g., trim/normalize case) while preserving display names in metadata if needed.
- Require admin auth; rate limit similar to other settings endpoints.
- Consider basic defense-in-depth linting (e.g., ban catastrophic regex like nested repeats) — optional.

---

**Testing Plan (pytest)**
Add targeted tests under `tests/` (markers: unit/integration):
- Unit: taxonomy loader
  - When DB empty → loads file; when DB set → loads DB; force_reload clears cache.
  - Invalid DB payload (no categories) → falls back to file or returns None and logs warning.
- API: PUT/GET lifecycle
  - PUT with valid JSON saves to DB and invalidates cache.
  - PUT with invalid regex returns 400.
  - GET returns DB value when present; file content otherwise.
- Integration: runtime consumers
  - Patch DB taxonomy to add a new synonym; assert `ContentRouter.detect_content_types` sees it immediately after invalidation.
  - Simulate reindex flow is out of scope for automated tests here, but add a docnote in the test explaining the `POST /refresh` path.

Do not modify unrelated tests. Keep coverage for `backend/core` steady or improved.

---

**Operational Considerations**
- Bootstrap: On first run, do not auto-write defaults into DB. Use file as default, and write only on first successful PUT to keep behavior simple and transparent.
- Rollback: Keep `backend/core/topic_taxonomy.json` as a known-good baseline; provide a “Reset to Default” UI action that fetches from file (or ships a static example) and requires explicit Save.
- Observability: Log taxonomy source (DB vs file) at app init; include category count in logs (already present) for sanity.
- Cache: The taxonomy cache lives in `taxonomy_loader`; it is separate from `SettingsManager`’s TTL cache and should be invalidated immediately on update.

---

**Estimated Work Breakdown**
- API endpoints (GET/PUT + validation + audit): ~150–250 LOC
- Loader DB fallback and cache invalidation: ~40–80 LOC
- Frontend service + page wiring (load/save, toasts, optional refresh CTA): ~80–150 LOC
- Tests (loader + API + small integration): ~120–200 LOC
- QA pass and docs update: 0.5–1 day

---

**Risks & Mitigations**
- Regex performance or ReDoS: compile and optionally limit pattern complexity; consider timeouts during classification (future enhancement).
- Drifting categories vs. existing metadata: taxonomy changes won’t retroactively update previously indexed chunks until reindex; clearly surface reindex step.
- Inconsistent ignore words: `QueryRouter` still hardcoded — document as a follow-up enhancement to pull from taxonomy `router.ignore_words`.

---

**Acceptance Criteria**
- Admin can GET/PUT taxonomy via API; invalid JSON/regex rejected with clear errors.
- Taxonomy is persisted in SQLite (`admin_settings`), visible via GET and `admin_db_manager`.
- `get_topic_taxonomy()` returns DB-backed taxonomy after save, without restart.
- Query intent detection reflects new taxonomy immediately after save.
- Documentation in Admin UI informs that classification will fully apply after a reindex.

---

References
- UI: `admin/frontend/src/views/settings/TaxonomySettings.vue`, `admin/frontend/src/services/api.js`
- File taxonomy: `backend/core/topic_taxonomy.json`
- Loader: `backend/core/taxonomy_loader.py`
- Consumers: `backend/core/content_router.py`, `backend/core/startup_content_classifier.py`
- Admin DB: `backend/core/admin_database.py` (table `admin_settings` + helpers)
- Settings infra: `backend/core/settings_manager.py`, `backend/core/settings_schemas.py`
- Refresh endpoint: `backend/routes/admin_refresh.py` (reindex flag)
