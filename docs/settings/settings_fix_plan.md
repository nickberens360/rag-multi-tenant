# Settings Hardening and Alignment Plan

Goal: Eliminate settings drift between admin UI and runtime, fix broken paths, and make settings application reliable, testable, and easy to operate.

---

## Objectives
- Single source of truth for each configuration domain.
- Immediate and predictable application of changes (or explicit TTL/“apply now”).
- Remove/repair dead or misleading UI controls and API calls.
- Ensure backend reads DB settings consistently with sane fallbacks.
- Cover with tests and lightweight observability.

## Scope
- Admin frontend: settings pages, stores, and services under `admin/frontend/src`.
- Backend: settings endpoints in `backend/routes/admin.py`; settings manager/schemas; runtime consumers (LLM selection, retrieval, routing, logging, middleware).

## Risks & Constraints
- Backward compatibility with existing `admin_settings` records.
- Avoid user-visible disruption in admin UI.
- Keep changes minimal and targeted; no broad refactors.

---

## Plan of Record

### 1) Response Provider Source of Truth
- Issue: Response provider can be set in System Settings, but runtime uses ResponseSettings.
- Actions:
  - Frontend: In System Settings, make provider fields read-only or remove; add helper text pointing to Core/Response Settings page.
  - Backend: Keep legacy mapping (SystemConfigurationSettings.from_dict) but treat `response_llm` in ResponseSettings as authoritative.
  - Validation: On `PUT /settings/system-config`, ignore or warn if response-LLM-related fields differ from ResponseSettings.
- Acceptance:
  - Changing provider in Core/Response Settings changes runtime; System Settings changes don’t mislead admins.

### 2) Response Caching Toggles → Runtime
- Issue: UI toggles not applied; `llm_chain` uses env `ENABLE_CACHING`/`CACHE_TTL`.
- Actions:
  - Backend: In `llm_chain`, read `settings_manager.get_response_settings()` for `enable_caching` and `cache_ttl_seconds`; env vars become fallback defaults.
  - Document precedence (DB overrides env), and feature-flag a short-term fallback env override if needed.
- Acceptance:
  - Toggling caching and TTL in admin takes effect after save (subject to cache).

### 3) Routing/Search Thresholds Wiring
- Issue: `similarity_threshold`, `fuzzy_threshold`, `max_search_results` not used; split between QueryRoutingSettings and SearchRetrievalSettings.
- Actions:
  - Decide consolidation: prefer one schema (recommend QueryRoutingSettings for query-time behavior; keep RAG for vector thresholds).
  - Apply selected fields in routing path (e.g., fallback strategies and confidence thresholds) and in retriever parameters where relevant.
  - Mark unused fields deprecated and hide in UI or add help text.
- Acceptance:
  - Documented semantics; thresholds affect behavior; no dead UI controls.

### 4) Fix Search & Retrieval Page RAG Save Bug
- Issue: Calls non-existent `updateRagConfigSettings` on `adminAPI`.
- Actions:
  - Frontend: Use the existing Rag Config service (`ragConfigSettingsService`) for RAG updates or remove the duplicate RAG controls from that page and link to RAG page.
- Acceptance:
  - No 404/undefined errors; saving RAG from UI works through the RAG page only.

### 5) Feature Flags Cleanup
- Issue: Page shows legacy fields (and RAG) not read by runtime.
- Actions:
  - Frontend: Remove/hide non-functional flags (e.g., RAG toggles, caching flags). Keep `enable_debug_mode`, `enable_maintenance_mode`, `enable_api_versioning`, UX flags.
  - Backend: Maintain `is_feature_enabled` mappings for compatibility but minimize cross-schema indirection in the UI.
- Acceptance:
  - Feature Flags page only contains active, meaningful flags.

### 6) Security Settings → Logger & Middleware
- Issue: `anonymize_ips` and `excluded_ips` read from env; DB values ignored.
- Actions:
  - Backend: Update `sqlite_query_logger` to read SecuritySettings at init and on a timed refresh or per-request cache (e.g., 60s TTL), with env as boot defaults.
  - Define precedence: DB overrides env once available.
- Acceptance:
  - Changing anonymization/exclude list in admin affects logging; behavior documented.

### 7) Cache Invalidation & TTL Clarity
- Issue: Settings cache (5 min) causes stale reads; only some endpoints invalidate.
- Actions:
  - Backend: On each `PUT` settings endpoint, call `settings_mgr.invalidate_cache(<key>)`.
  - Frontend: Add “Apply now” button (calls `/settings/cache/invalidate`) post-save; show cache status in UI (keys, TTL seconds).
  - Docs: Note TTL and immediate-apply option.
- Acceptance:
  - After saving, admins can apply immediately; otherwise changes propagate within TTL.

### 8) Tests
- Unit tests:
  - settings_schemas: parsing/validation defaults and ranges.
  - settings_manager: get/set per schema, cache invalidation.
- Integration tests (FastAPI):
  - Each `GET/PUT` endpoint round-trip and persistence.
  - Verify cache invalidation per endpoint.
- Runtime behavior tests:
  - LLM selection reflects ResponseSettings.
  - SemanticSearcher reads RAG config.
  - App factory rate limiting reflects SecuritySettings.
  - Optional: Caching behavior toggles in `llm_chain` if wired.
- Acceptance:
  - Tests pass locally and in CI; coverage maintained or improved.

### 9) Migration & Compatibility
- Data migration:
  - Ensure existing `admin_settings` records map cleanly (keep current migration helpers in schemas).
  - Optionally create a one-time migration to remove orphan flags or move values to new keys.
- Rollback plan:
  - Feature-gate new runtime reads; fallback to env/defaults on error.

### 10) Observability & Safety
- Logging:
  - Log settings loads and cache invalidations at INFO.
  - Warn on deprecated fields received.
- Admin visibility:
  - Expose a read-only “Effective settings” summary endpoint (sanitized) for debugging.

---

## Milestones & Deliverables

1. Hotfixes (1 PR)
- Fix RAG save path in Search & Retrieval page or remove duplicate controls.
- Add cache invalidation on all `PUT` endpoints.
- Create “Apply now” button in admin.

2. Provider & Caching Alignment (1–2 PRs)
- Make System Settings provider read-only; add UI help.
- Wire ResponseSettings caching into `llm_chain` with env fallback.

3. Security & Routing (1–2 PRs)
- Apply SecuritySettings anonymize/exclude in logger.
- Wire agreed routing thresholds or remove dead UI.

4. Cleanup & Tests (1 PR)
- Feature Flags page cleanup.
- Test suite additions across schemas, routes, and runtime consumers.

---

## Acceptance Criteria
- No dead or misleading controls in admin.
- All settings pages save without errors and are reflected in DB.
- Runtime respects ResponseSettings provider and (if implemented) caching.
- RAG settings continue to influence retrieval thresholds and MMR.
- Security settings influence rate limiting, analytics, and (post-change) IP anonymization/exclusions.
- Cache invalidate available via UI and API; TTL documented.
- Tests cover parsing, persistence, and main runtime consumers.

---

## Out of Scope (for now)
- Full redesign of settings architecture.
- Multi-tenant settings or per-user overrides.
- Moving secrets management beyond current encrypted API keys.

---

## Files Likely Touched (when implementing)
- Frontend: `admin/frontend/src/views/settings/*.vue`, `admin/frontend/src/stores/*`, `admin/frontend/src/services/*`.
- Backend: `backend/routes/admin.py`, `backend/core/settings_manager.py`, `backend/core/settings_schemas.py`, `backend/core/llm_chain.py`, `backend/core/sqlite_query_logger.py`, `backend/core/app_factory.py`.

