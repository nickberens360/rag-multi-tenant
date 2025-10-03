# Parallel Execution Plan — Settings Refactor

## Purpose
Coordinate multiple AI agents to deliver the settings refactor in parallel with minimal merge conflicts. Each agent works in an isolated Git worktree and focused branch, touching disjoint files where possible. Integration is owned by a single agent to reduce churn.

References
- Primary design: `docs/settings-refactor-plan.md`
- Implementation playbook: `docs/settings-update-implementation-plan.md`

## Ground Rules
- One worktree + branch per workstream below.
- Agents must not edit files outside their declared scope.
- Run `pre-commit install` inside the worktree.
- Before opening a PR: `git fetch origin && git rebase origin/development` (from your worktree).
- No secrets in logs or docs. Never print key values.

## Workstreams / Phases

### A1 — Inventory & Classification (docs-only)
- Goal: Enumerate all settings (env, DB, defaults) and where they are used.
- Files (new only):
  - `docs/reports/settings-inventory.json`
  - `docs/reports/settings-inventory.md`
- Code changes: none.
- Commands:
  - `git worktree add -b chore/settings-inventory ../wt-settings-inventory origin/development`
- Tasks:
  - Discover env access: `rg -n "os.getenv\(" backend`
  - Discover AppConfig usage: `rg -n "\bAppConfig\.(get_|[A-Z_]+)" backend`
  - Discover settings_manager reads: `rg -n "get_.*_settings\(|get_system_config_settings\(|get_response_settings\(" backend`
  - Output inventory JSON (key_name, source_type, code_refs, sensitive, notes)
  - Summarize proposals in the MD file

### A2 — Settings Manifest + Validation (new module + tests)
- Goal: Provide canonical lists and validation utilities.
- Files (new only):
  - `backend/core/settings_manifest.py`
  - `tests/test_settings_manifest.py`
- Code integration: none (do NOT edit `backend/main.py` here).
- Commands:
  - `git worktree add -b feat/settings-manifest-validation ../wt-settings-manifest origin/development`
- Tasks:
  - Add `ADMIN_MANAGED_SETTINGS`, `ENV_ONLY_SETTINGS`, `ENV_DB_NAME_MAP`
  - Implement `validate_configuration()` with fail-fast for required env-only keys
  - Unit tests: required key missing → raises; name mapping correctness

### A3 — Diagnostics Endpoint (new router + tests)
- Goal: Readiness/health visibility without secrets.
- Files (new only):
  - `backend/routes/admin_diagnostics.py`
  - `tests/test_admin_diagnostics.py`
- Code integration: none (A6 wires router into app).
- Commands:
  - `git worktree add -b feat/admin-diagnostics-endpoint ../wt-admin-diagnostics origin/development`
- Tasks:
  - Endpoint `GET /api/admin/diagnostics` returns:
    - `environment`: `ENVIRONMENT` or fallback to `RAILWAY_ENVIRONMENT`
    - `env_variables`: { total, missing, status: {KEY: ✓/✗} }
    - `admin_settings`: { total, configured, status: {key: ✓/✗} }
    - `health`: OK/ERROR based on missing required envs
  - DO NOT return secret values (presence only)
  - Unit tests for structure and no secret leakage

### A4 — Migration + Env Tooling (scripts + docs)
- Goal: One-time infra migration and env sync/validation.
- Files (new only):
  - `backend/scripts/migrate_settings_to_env.py`
  - `scripts/sync-environments.sh`
  - `scripts/validate-deployment.sh`
  - Optional doc updates in `docs/`
- Commands:
  - `git worktree add -b feat/settings-migration-scripts ../wt-settings-migration origin/development`
- Tasks:
  - Export non-admin-managed keys to `.env.infrastructure` using name mapping
  - Delete those keys from DB (idempotent; consider `--dry-run`)
  - Sync tooling via Railway CLI + `jq` (see implementation plan)
  - Validate required keys from `scripts/required-env.txt` (no counts)

### A5 — Admin UI Simplification (flags only)
- Goal: Hide infra/advanced settings via flags; avoid router churn now.
- Files (new + minimal edits):
  - New: `admin/frontend/src/config/featureFlags.ts`
  - Minimal conditional rendering in settings views (do not remove routes yet)
- Commands:
  - `git worktree add -b feat/admin-settings-simplify-flag ../wt-admin-simplify origin/development`
- Tasks:
  - Introduce `ADMIN_HIDE_INFRA_SETTINGS` flag (default false)
  - Guard infra/advanced UI with v-if based on the flag
  - Ensure local build passes; no route deletions

### Phase 5 — Integration (centralized wiring)
- Goal: Single agent integrates A2/A3 safely behind feature flag.
- Files (existing, minimal edits):
  - `backend/main.py` (call `validate_configuration()` with try/except; optional flag-aware log)
  - `backend/core/app_factory.py` (include `admin_diagnostics` router)
  - Optional tiny adjustments in `backend/core/config_v2.py` if needed (avoid churn)
- Commands:
  - `git worktree add -b chore/settings-integration ../wt-settings-integration origin/development`
- Tasks:
  - Add env flag `USE_NEW_CONFIG_SYSTEM` (default false) consumed in startup
  - Wire diagnostics router into the app under `/api/admin`
  - Call validation at startup; do not change runtime precedence yet

### Phase 6 — Tests & CI Hardening (tests only)
- Goal: Expand tests without touching production code.
- Files (new only):
  - `tests/` additions; `tests/conftest.py` if needed
- Commands:
  - `git worktree add -b chore/settings-tests-ci ../wt-settings-tests origin/development`
- Tasks:
  - Add tests to exercise A2/A3 behaviors
  - Ensure `pytest -q` passes locally and in CI

## Integration & Merge Order
1) A1 (docs only)
2) A2 and A3 (new files + tests, independent)
3) Phase 6 (tests only)
4) Phase 5 (integration wiring)
5) A4 (scripts/docs)
6) A5 (UI flags)

## Conflict Boundaries
- Only Phase 5 edits: `backend/main.py`, `backend/core/app_factory.py` (integration points)
- A2: adds a new module + its tests; no edits to existing modules
- A3: adds a new router + its tests; app wiring deferred to Phase 5
- A4: scripts and docs only
- A5: feature flags + minimal conditional rendering; avoid router edits
- Phase 6: tests only

## Branch & Worktree Conventions
- Branch naming: `feat/...` for features, `chore/...` for non-functional, `docs/...` for docs
- Create worktree: `git worktree add -b <branch> ../<wt-dir> origin/development`
- Rebase before PR: `git fetch origin && git rebase origin/development`
- Remove after merge: `git worktree remove ../<wt-dir>`

## PR Checklist (per agent)
- Scope limited to declared files
- No secrets exposed in code or tests
- Tests updated/added and passing locally
- Rebased on `origin/development`
- Updated relevant docs (link to this plan and the implementation plan)

## Definition of Done (per workstream)
- A1: Inventory JSON + summary MD ready
- A2: Manifest + validation module with tests
- A3: Diagnostics router + tests
- A4: Migration + sync + validation scripts documented and runnable
- A5: Flags hide infra UI; build passes
- Phase 5: Validation wired at startup; router included; flag default false
- Phase 6: CI passes with stable or improved coverage

## Rollback & Safety
- Feature flag: `USE_NEW_CONFIG_SYSTEM=false` means runtime remains DB-first until cutover
- A4 scripts are idempotent and support dry-run; do not auto-apply in CI
- Railway rollback available for deployments

## Communication
- Use branch names from this doc so reviewers can map changes quickly
- Cross-reference this plan in each PR description
- Integration owner (Phase 5) coordinates merges and resolves any wiring conflicts
