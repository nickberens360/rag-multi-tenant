Multi‑Tenant Hardening Agent Prompt

Goal: finish multi-tenant hardening across backend + admin frontend so data is always tenant-scoped and re-fetches when switching orgs.

Context files to read first
- docs/multi-tenant/issues/README.md
- docs/multi-tenant/issues/CONTEXT.md
- docs/multi-tenant/issues/tasks.yaml (canonical task list)
- docs/multi-tenant/issues/PROGRESS.yaml (what’s pending)

Scope to implement now (pending in PROGRESS.yaml)
1) backend_followup_reads_explicit_tenant_filter
2) backend_admin_settings_reads_explicit_tenant_filter
3) frontend_reactivity_settings_views

Backend changes (FastAPI/SQLAlchemy)
General pattern for explicit tenant filter (use in WHERE/AND):
- tenant_filter SQL fragment:
  `tenant_id = COALESCE(NULLIF(current_setting('app.tenant_id', true), '')::uuid, CAST(:fallback_tid AS uuid))`
- Param to pass on every such query:
  `"fallback_tid": str(getattr(request.state, "tenant_id", None) or os.getenv("DEFAULT_TENANT_ID") or "00000000-0000-0000-0000-000000000001")`

A) Follow-up reads — backend/routes/admin.py
- GET /settings/followup/categories (function `get_followup_categories`):
  - Add tenant_filter to WHERE. If active_only filtering exists, combine with AND.
- GET /settings/followup/questions (function `get_followup_questions`):
  - Add tenant_filter to the dynamic `where` list.
- GET /settings/followup/categories/{category_id}/stats (function `get_followup_category_stats`):
  - Ensure the category exists for current tenant:
    `SELECT id FROM followup_categories WHERE id=:id AND <tenant_filter>` (404 if not found).
  - Optional: add tenant_filter to the COUNT(*) from followup_questions to be explicit:
    `WHERE category_id=:id AND <tenant_filter>`

B) Settings reads — backend/routes/admin.py
- For all reads from `admin_settings` and `taxonomy_settings_history`:
  - Add tenant_filter to SELECTs so superuser sessions cannot see other tenants.
  - Search and patch:
    - `FROM admin_settings`
    - `FROM taxonomy_settings_history`
  - Example change:
    `SELECT setting_value FROM admin_settings
     WHERE setting_key = 'taxonomy_settings'
     AND tenant_id = <tenant_filter>
     LIMIT 1`
  - Ensure `:fallback_tid` param is supplied in execute(...).

Notes
- Do not change INSERT/UPSERT code that is already tenant safe.
- Keep DB access via dependency `pg_session: Session = Depends(get_db_session)` where used.

Frontend changes (Vue/Pinia)
Add tenant-change watchers to reload settings pages. Use this pattern:
- In each settings view’s `<script setup>`:
  `import { storeToRefs } from 'pinia'
   import { useTenantStore } from '@/stores/tenant'
   import { watch } from 'vue'

   const tenantStore = useTenantStore()
   const { currentTenant } = storeToRefs(tenantStore)

   // call the same loader used on mount
   watch(currentTenant, async (n, o) => {
     if (o && n && o.id !== n.id) {
       await loadDataOrExistingFetchMethod()
     }
   }, { deep: true })`

Update the following view files to reload on org switch:
- admin/frontend/src/views/settings/CoreSettings.vue
- admin/frontend/src/views/settings/KnowledgeSettings.vue
- admin/frontend/src/views/settings/TaxonomySettings.vue
- admin/frontend/src/views/settings/ResponseSettings.vue
- admin/frontend/src/views/settings/SecuritySettings.vue
- admin/frontend/src/views/settings/FeatureSettings.vue

Implementation notes
- Reuse each file’s existing load method (the one called in onMounted). If no helper exists, wrap the initial fetch logic in one.
- Do not add tenant-change watchers where they already exist (avoid duplicates).
- Keep code style consistent and changes minimal.

Validation checklist
- Backend grep checks:
  - `rg -n "FROM followup_categories|FROM followup_questions" backend/routes/admin.py`
    Confirm tenant_filter added to SELECTs.
  - `rg -n "FROM admin_settings|taxonomy_settings_history" backend/routes/admin.py`
    Confirm tenant_filter added.
- Frontend grep checks:
  - For each updated settings view, ensure a watch on currentTenant exists and calls the view’s load method.
- Manual checks (optional):
  - Switch orgs; verify:
    - Settings pages reload with tenant-specific values.
    - Follow-up categories/questions list are correctly scoped per tenant.
    - Network calls go to `/{slug}/api/admin/...` endpoints.

Progress update
- After implementing and validating, update `docs/multi-tenant/issues/PROGRESS.yaml`:
  - `backend_followup_reads_explicit_tenant_filter: completed`
  - `backend_admin_settings_reads_explicit_tenant_filter: completed`
  - `frontend_reactivity_settings_views: completed`
- Add brief notes if anything noteworthy was encountered.

Constraints
- Avoid refactors beyond task scope.
- Do not introduce new dependencies.
- Maintain existing behavior and styles outside of tenant fixes.

