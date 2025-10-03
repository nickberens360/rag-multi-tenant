# Settings Update Implementation Plan (Agent Playbook)

## Overview
- Goal: Implement the two-tier configuration system defined in `docs/settings-refactor-plan.md` with zero downtime and feature parity.
- Outcome: Clear separation between env-only infrastructure config and admin-managed operational settings, with validation, diagnostics, and safe migration.
- Scope: Backend (FastAPI), Admin frontend (Vue), deployment tooling (Railway), documentation.

## Ground Rules
- Secrets: never print or log real values; use presence/missing indicators only.
- Naming: DB keys use `snake_case`; env keys use `UPPER_SNAKE_CASE`.
- Precedence: Admin-managed keys → DB overrides env. Env-only keys → no DB fallback.
- Mapping: Maintain explicit mapping between env and DB names for overlapping keys (see below).
- Tests: Add/adjust tests where indicated; keep or improve coverage.
- Rollout: Incremental and reversible; use feature flags and backups.

## References
- Primary design: `docs/settings-refactor-plan.md` (latest)
- Backend entrypoint: `backend/main.py`
- Config: `backend/core/config_v2.py`
- Settings system: `backend/core/settings_manager.py`, `backend/core/settings_schemas.py`
- Admin UI router: `admin/frontend/src/router/index.js`

## Timeline (4 Phases)
1) Impact Assessment (Week 1–2)
2) Incremental Migration (Week 3–8)
3) Infrastructure Settings Migration (Week 9–12)
4) Frontend Simplification (Week 13–16)

---

## Phase 1 — Impact Assessment (Week 1–2)
Objective: Build a complete inventory of current settings usage and dependencies.

Agent Tasks
- Enumerate env var usage in backend:
  - Search for env access: `rg -n "os.getenv\(" backend`
  - Search for config references: `rg -n "\bAppConfig\.(get_|[A-Z_]+)" backend`
  - Search for settings manager reads: `rg -n "get_.*_settings\(|get_system_config_settings\(|get_response_settings\(" backend`
- Catalog admin-managed resources:
  - Followup questions tables and APIs: `rg -n "followup_questions" backend`
  - Security/rate limit schema: `rg -n "enable_rate_limiting|rate_limit_" backend`
- Produce inventory artifact:
  - Create `docs/reports/settings-inventory.json` with entries:
    - key_name
    - source_type: env|db|code_default
    - code_refs: [file:line]
    - sensitive: boolean
    - notes
- Identify candidates for env-only vs admin-managed using the rules in the refactor plan.

Acceptance Criteria
- An inventory JSON listing all keys with usage locations.
- A short summary in `docs/reports/settings-inventory.md` with proposed classification deltas.

---

## Phase 2 — Incremental Migration (Week 3–8)
Objective: Introduce manifest + validation + feature flag without breaking behavior.

Agent Tasks
1) Settings Manifest (read-only integration)
- Create `backend/core/settings_manifest.py` with two dicts:
  - `ADMIN_MANAGED_SETTINGS`: 15 curated keys with type info (include optional OpenAI key)
  - `ENV_ONLY_SETTINGS`: env-only infra keys with required/default flags
- Include an `ENV_DB_NAME_MAP` for explicit mapping, e.g.:
  - `PRIMARY_LLM` ↔ `primary_llm`
  - `CLAUDE_MODEL` ↔ `claude_model`
  - `GEMINI_MODEL` ↔ `gemini_model`
  - `MAX_RESULTS` ↔ `max_results`
  - `CACHE_TTL` ↔ `cache_ttl`, `ENABLE_CACHING` ↔ `enable_caching`

2) Validation Utilities
- Add a `validate_configuration()` function in `settings_manifest.py` that:
  - Fails fast on missing required env-only keys (raise a clear exception)
  - Returns a typed summary for diagnostics
- Hook validation at startup (non-destructive):
  - In `backend/main.py` (during startup), call validation and log concise results.

3) Feature Flag and Read Path
- Add env `USE_NEW_CONFIG_SYSTEM` (default: false). Keep codepaths as-is when false.
- If true: ensure admin-managed reads use DB; env-only reads never consult DB.
  - This is a documentation-only toggle initially; no behavior change until Phase 3.

4) Diagnostics Endpoint
- Add `/api/admin/diagnostics` (or extend existing admin route) that returns:
  - `environment`: `ENVIRONMENT` or fallback to `RAILWAY_ENVIRONMENT`
  - `env_variables`: { total, missing, status: {KEY: ✓/✗} }
  - `admin_settings`: { total, configured, status: {key: ✓/✗} }
  - `health`: OK/ERROR based on missing required envs
- Never return secret values. Presence indicators only.

5) Tests (Backend)
- Add unit tests under `tests/`:
  - Validation: missing/required envs → raises with clear message
  - Mapping: env↔DB name resolution works as expected
  - Diagnostics: includes presence flags only; no secrets

Acceptance Criteria
- `settings_manifest.py` exists with curated lists + mapping.
- Validation integrated into startup logging without breaking the app.
- Diagnostics endpoint returns expected structure (presence only).
- Tests pass locally: `pytest -q`.

---

## Phase 3 — Infrastructure Settings Migration (Week 9–12)
Objective: Move infra config to env, add sync/validation tooling, and finalize precedence.

Agent Tasks
1) Migration Script
- Create `backend/scripts/migrate_settings_to_env.py` to:
  - Read all DB settings
  - For keys not in `ADMIN_MANAGED_SETTINGS`, export to `.env.infrastructure`
  - Use name mapping for env keys
  - Delete migrated keys from DB (idempotent; dry-run option recommended)

2) Env Parity & Sync Tooling
- Create `scripts/sync-environments.sh`:
  - Export source env as JSON using Railway CLI
  - Apply to target env using `railway variables set`
  - Include allowlist/denylist toggles for secrets if desired
- Create `scripts/validate-deployment.sh`:
  - Validate presence of required keys from `scripts/required-env.txt`
  - Hit health and diagnostics endpoints

3) Precedence Enforcement
- Under `USE_NEW_CONFIG_SYSTEM=true`:
  - Ensure env-only keys are read from env exclusively
  - Ensure admin-managed keys read from DB (with env as seed/default only)
  - Clarify in code comments where env seeds are consumed (e.g., migration or first-run defaults), not at runtime

4) Security
- Confirm API keys are exclusively retrieved through `ApiKeyManager` (DB encrypted); never fall back to env at runtime after cutover.
- `API_KEY_ENCRYPTION_SECRET` must be set in production; enforce via validation.

5) Tests
- Add tests for migration script (dry-run mode) and precedence rules.

Acceptance Criteria
- Migration can export infra settings and remove them from DB safely (dry-run verified).
- Sync and validation scripts work in local/CI contexts (within sandbox limits).
- With `USE_NEW_CONFIG_SYSTEM=true`, precedence rules behave as specified.

---

## Phase 4 — Frontend Simplification (Week 13–16)
Objective: Hide/remove admin UI for env-only settings and simplify remaining views.

Agent Tasks
- Router: In `admin/frontend/src/router/index.js`, keep only routes for:
  - API keys, content/search, performance, models, security/rate-limiting
- Remove/hide infrastructure & advanced settings sections.
- Ensure SPA base remains `/settings` (served under `/admin/settings`).
- Build and verify no dead links remain; update navigation labels as needed.

Acceptance Criteria
- Only ~15 relevant settings appear in admin UI.
- No references to env-only settings remain in admin routes or forms.

---

## Explicit Env↔DB Name Mapping (Seed/Overlay)
- `PRIMARY_LLM` ↔ `primary_llm`
- `CLAUDE_MODEL` ↔ `claude_model`
- `GEMINI_MODEL` ↔ `gemini_model`
- `MAX_RESULTS` ↔ `max_results`
- `CACHE_TTL` ↔ `cache_ttl`
- `ENABLE_CACHING` ↔ `enable_caching`
- `RATE_LIMIT` ↔ `rate_limit` (display string)

Notes
- OpenAI: `OPENAI_API_KEY` optional/future; document as such in the manifest and UI.
- Thresholds: `search_threshold` is 0–100 UI scale; map to 0–1 internally if needed. `retrieval_score_threshold` stays 0.1–0.9.

---

## Reindex Flow (Embedding/Chunking Changes)
- Pause ingestion/background sync
- Backup current vector store
- Rebuild all embeddings
- Validate retrieval metrics (sample queries)
- Deploy config and switch traffic
- Remove old vectors after stabilization

---

## Security & Privacy Checklist
- Do not log or return secret values in diagnostics.
- Enforce required secrets in validation (`API_KEY_ENCRYPTION_SECRET`, `IP_HASH_SALT`, admin bootstrap password in prod).
- Ensure `CORS_ORIGINS` is validated via `AppConfig` helper.

---

## Rollback Plan
- Per-phase rollback:
  - Phase 2: Disable `USE_NEW_CONFIG_SYSTEM`, revert to DB-first logic.
  - Phase 3: Re-import `.env.infrastructure` into DB if needed; re-enable DB reads for affected keys.
  - Phase 4: Restore hidden routes/components from VCS.
- Railway one-click rollback to previous deployment.

---

## Acceptance Criteria (Global)
- Diagnostics endpoint: all green in both dev and prod.
- Backend tests pass (`pytest -q`) and coverage is stable or improved.
- Admin UI shows only relevant (~15) settings.
- Deployments require no manual hotfixes for configuration.

---

## Task Board (Agent Checklist)
- [ ] Phase 1: Inventory JSON + summary MD
- [ ] Phase 2: Manifest + validation + diagnostics + tests
- [ ] Phase 3: Migration + sync/validate scripts + precedence enforcement + tests
- [ ] Phase 4: Admin UI simplification
- [ ] Final verification: diagnostics all green, docs updated

---

## Notes for Agents
- Prefer minimal, reviewable PRs per subtask; include links to this playbook.
- Use ripgrep (`rg`) for discovery; keep outputs small and focused.
- When in doubt, defer to the latest `docs/settings-refactor-plan.md` for scope decisions.
