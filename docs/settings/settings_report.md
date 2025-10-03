# Admin Settings End-to-End Verification Report

This report verifies that admin settings write to the DB correctly and are consumed by backend code at runtime. Path traced: Admin UI → API → backend route/schema → DB → runtime usage.

- Date: 2025-09-09
- Scope: `admin/frontend/src/views/settings/*`, Pinia stores/services, `backend/routes/admin.py`, `backend/core/*`.

---

## Summary

- DB writes: All settings pages persist successfully via admin routes to `admin_settings` or normalized tables.
- Runtime consumption: RAG, response provider (via ResponseSettings), and rate limiting/analytics are applied. Several others are not currently used by runtime (noted below).
- Key issues:
  - Response provider set in System Settings is ignored; runtime uses ResponseSettings.
  - Response caching toggles in UI do not affect runtime (env-driven in code).
  - Feature Flags page contains legacy/RAG fields not read by runtime.
  - Search & Retrieval page attempts non-existent `updateRagConfigSettings` (save fails there; use RAG page).
  - Settings cache (5 min TTL) can delay application of new values unless invalidated.

---

## Findings by Category

### System Configuration
- Frontend: `SystemSettings.vue`, `CoreSettings.vue` → `get/updateSystemConfigSettings`.
- Backend: `GET/PUT /api/admin/settings/system-config` → `SystemConfigurationSettings` under `system_config_settings`.
- Runtime: Processing LLM honored (indexing); Response LLM from here is NOT used for chat.
- Verdict: Writes OK; processing model applied; chat provider must be set in Response Settings.

### Response Settings
- Frontend: `ResponseSettings.vue` + store → `get/updateResponseSettings`.
- Backend: `GET/PUT /api/admin/settings/response` → `ResponseSettings` under `response_settings`.
- Runtime: Response provider/model and smart selection applied; formatting prefs used in system prompt.
- Gap: `enable_caching`/`cache_ttl_seconds` not used; runtime caching controlled by env in `llm_chain`.
- Verdict: Writes OK; provider/formatting honored; caching toggles ignored.

### Core Settings (page)
- Aggregates saves for ResponseSettings (response provider/models), SystemConfig (processing LLM), FeatureFlags; API Keys overview.
- Use this page to change response provider (runtime-effective).

### Feature Flags
- Frontend: `FeatureSettings.vue` + store.
- Backend: `GET/PUT /api/admin/settings/features` → `FeatureFlags`.
- Runtime mapping:
  - enable_analytics, enable_rate_limiting → SecuritySettings
  - enable_smart_routing → QueryRoutingSettings
  - enable_caching/enable_response_caching → ResponseSettings
- Page includes legacy/RAG flags not read by runtime.
- Verdict: Writes OK; only proper FeatureFlags matter; ignore RAG/caching flags here.

### Routing Settings
- Frontend: `RoutingSettings.vue` + store.
- Backend: `GET/PUT /api/admin/settings/routing` → `QueryRoutingSettings` under `routing_settings`.
- Runtime: `enable_smart_routing` honored; thresholds (`similarity_threshold`, `fuzzy_threshold`, `max_search_results`) not wired into current routing/search logic.
- Verdict: Writes OK; smart routing toggle impacts runtime.

### Search & Retrieval Settings
- Frontend: `useSearchRetrievalSettingsStore`.
- Backend: `GET/PUT /api/admin/settings/search-retrieval` → `SearchRetrievalSettings`.
- Runtime: Not referenced by active retrieval/routing; RAG behavior controlled by RAG config.
- UI bug: Page calls `apiService.updateRagConfigSettings` (missing) → use RAG page.
- Verdict: Writes OK; not consumed.

### RAG Configuration
- Frontend: `RagConfigSettings.vue` + store/service (direct axios to `/settings/rag-config`).
- Backend: `GET/PUT /api/admin/settings/rag-config` → `RagConfigurationSettings` under `rag_config_settings`.
- Runtime: Used by `SemanticSearcher` (`rag_score_threshold`, `rag_use_mmr`, `rag_mmr_*`, `rag_use_heading_splitter`, `rag_index_dirs`).
- Verdict: Fully wired and applied.

### Security Settings
- Frontend: `SecuritySettings.vue`.
- Backend: `GET/PUT /api/admin/settings/security` → `SecuritySettings`.
- Runtime: Rate limiting and analytics toggles honored (`app_factory`, `sqlite_query_logger`). `anonymize_ips`/`excluded_ips` not applied (logger reads env). Session fields not used elsewhere.
- Verdict: Writes OK; rate limiting & analytics applied; IP/log/session fields not consumed.

### Follow-up (Settings, Categories, Questions)
- Frontend: `UXSettings.vue`, `FollowupSettings.vue` and related components.
- Backend: `GET/PUT /api/admin/settings/followup` + normalized CRUD.
- Runtime: `FollowUpService` reads normalized tables + settings; cache cleared after updates.
- Verdict: Fully wired and applied.

### API Keys
- Frontend: `ApiKeysSettings.vue`, subset in `CoreSettings.vue`.
- Backend: `/api/admin/settings/api-keys*` encrypted CRUD.
- Runtime: `llm_chain`/`app_initializer_v2` resolve keys via `api_key_manager`.
- Verdict: Fully wired and applied.

---

## Settings Cache

- Settings cached ~5 min in `SettingsManager`.
- Only System Config update explicitly invalidates cache; other updates may be delayed until TTL.
- Admin routes exist to view/invalidate cache; no explicit UI button identified.

---

## Notable Issues & Risks

1) Response provider split: System Settings provider has no effect; ResponseSettings is authoritative.

2) Response caching toggles ignored: UI toggles do not control runtime caching (env-driven).

3) Feature Flags drift: Legacy/RAG fields shown but not read; can confuse admins.

4) Search & Retrieval RAG save bug: Non-existent API method used; use RAG page.

5) Security IP/log settings not applied: DB values not used by logger; env is used instead.

6) Unused thresholds: Several Routing/Search thresholds persisted but not used in current flow.

---

## Guidance for Admins

- Change chat response provider/models in Core Settings (updates ResponseSettings).
- Manage RAG in the RAG Configuration page.
- Rate limiting/analytics in Security Settings take effect (subject to cache TTL).
- Invalidate settings cache after critical changes to apply immediately.
- Treat Feature Flags as system/UX flags only; ignore RAG/caching flags there.

---

## Optional Follow-ups (no code changes made)

- UI: Clarify System vs Response provider; hide/label legacy/RAG flags; fix/remove bad RAG save on Search & Retrieval page.
- Runtime: Optionally honor ResponseSettings caching in `llm_chain`; wire thresholds as needed; apply SecuritySettings IP/log fields in logger.
- UX: Add an “Apply now” action to call `/settings/cache/invalidate` post-save.

---

## References

- Frontend API/services/stores: `admin/frontend/src/services/api.js`, `admin/frontend/src/services/settings/*`, `admin/frontend/src/stores/*`.
- Settings pages: `admin/frontend/src/views/settings/*.vue`.
- Backend routes: `backend/routes/admin.py` (settings endpoints).
- Schemas/manager: `backend/core/settings_schemas.py`, `backend/core/settings_manager.py`.
- Runtime usage: `backend/core/llm_chain.py`, `backend/core/app_initializer_v2.py`, `backend/core/semantic_searcher.py`, `backend/core/query_router.py`, `backend/core/sqlite_query_logger.py`, `backend/core/app_factory.py`.

