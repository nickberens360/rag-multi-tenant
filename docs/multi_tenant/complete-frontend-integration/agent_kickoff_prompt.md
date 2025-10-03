Complete Frontend Integration — Agent Prompt

Goal: finish tenant-aware frontend integration in Astro by (a) implementing robust tenant-aware routing across pages and (b) adding proper error boundaries when tenant resolution fails.

Context files to read first
- docs/multi_tenant/complete-frontend-integration/issues/README.md
- docs/multi_tenant/complete-frontend-integration/issues/CONTEXT.md
- docs/multi_tenant/complete-frontend-integration/issues/tasks.yaml (canonical task list)
- docs/multi_tenant/complete-frontend-integration/issues/PROGRESS.yaml (what’s pending)
- docs/multi_tenant/agent_playbook.md (overall playbook and assumptions)

Scope to implement now (pending in PROGRESS.yaml)
1) frontend_astro_tenant_routing
2) frontend_tenant_resolution_error_boundaries

Astro tenant-aware routing (pages + helpers)
- Add an Astro middleware (`src/middleware.ts`) to resolve tenant slug from subdomain (prod) or path prefix (dev) and set `Astro.locals.tenantSlug`.
  - Prefer subdomain unless running on localhost; otherwise use the first path segment.
  - Normalize and validate slugs with a conservative regex (e.g., `^[a-z0-9][a-z0-9-]{1,30}$`).
  - Do not trust client headers for security; this is only for UX/routing.
- Ensure a dynamic route segment exists: `src/pages/[tenant]/...`.
  - Example: use `Astro.params.tenant` inside pages and build links with a helper `tenantHref(Astro, path)`.
- Root redirect: in `src/pages/index.astro`, redirect to `/${defaultTenant}` (from `PUBLIC_TENANT_DEFAULT_SLUG`) or render a tenant selector if unknown.
- Utility: create `src/utils/tenant.ts` with `tenantFromAstro(Astro)` and `tenantHref(Astro, path)` helpers to DRY path generation.

Example middleware (sketch)
```ts
// src/middleware.ts
import { defineMiddleware } from 'astro/middleware'

const TENANT_RX = /^[a-z0-9][a-z0-9-]{1,30}$/

export const onRequest = defineMiddleware(async (ctx, next) => {
  const host = ctx.url.hostname
  const path = ctx.url.pathname
  const isLocal = host.includes('localhost') || host === '127.0.0.1'

  const pathSlug = path.split('/').filter(Boolean)[0] || null
  const subdomain = host.split('.')[0]
  const slug = !isLocal && subdomain && !['www','api','admin'].includes(subdomain)
    ? subdomain
    : pathSlug

  ctx.locals.tenantSlug = slug && TENANT_RX.test(slug) ? slug : null
  return next()
})
```

Root redirect example
```ts
---
import { tenantFromAstro } from '../utils/tenant'

const defaultSlug = import.meta.env.PUBLIC_TENANT_DEFAULT_SLUG
if (defaultSlug) {
  return Astro.redirect(`/${defaultSlug}`)
}
---

<html><body>
  <p>Select an organization to continue.</p>
</body></html>
```

Error boundaries for tenant resolution failures
- Server-side guard: if a route under `/[tenant]/...` is accessed with an invalid or unknown slug, return a friendly 404 or redirect to `/tenant-not-found`.
  - Implement in `src/middleware.ts`: when `ctx.pathname` starts with `/${badSlug}` and `TENANT_RX` fails or slug cannot be resolved, short-circuit with a `404` response or redirect.
- Page-level guard: at the top of `src/pages/[tenant]/*.astro`, validate `Astro.params.tenant` and bail to an error page if invalid.
- Vue error boundary: create `src/components/TenantBoundary.vue` that uses `onErrorCaptured` to catch runtime errors in tenant-dependent components and render a fallback with guidance.
- Error page: add `src/pages/tenant-not-found.astro` with a clear message and link back to a safe landing page or selector.

Vue boundary example
```vue
<!-- src/components/TenantBoundary.vue -->
<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
const error = ref<unknown>(null)
onErrorCaptured((e) => { error.value = e; return false })
</script>

<template>
  <div v-if="error" class="tenant-error">
    <h3>We couldn’t load this organization</h3>
    <p>Please try again or switch organizations.</p>
    <slot name="fallback" />
  </div>
  <slot v-else />
  </template>
```

Validation checklist
- Grep checks:
  - `rg -n "defineMiddleware\(|onRequest" src/middleware.ts`
  - `rg -n "Astro\.params\.tenant|Astro\.locals\.tenantSlug" src/pages/[tenant]`
  - `rg -n "Astro\.redirect\(" src/pages/index.astro`
- Manual:
  - Unknown slug (e.g., `/does-not-exist`) renders `tenant-not-found` or 404 with a friendly page.
  - Known slug pages render and internal links keep the `/${slug}` prefix.
- Optional tests:
  - Add Vitest unit tests for `tenantFromAstro` parsing and link generation.

Progress update
- After implementing and validating, update `docs/multi_tenant/complete-frontend-integration/issues/PROGRESS.yaml`:
  - `frontend_astro_tenant_routing: completed`
  - `frontend_tenant_resolution_error_boundaries: completed`
  - Add brief notes if anything noteworthy was encountered.

Constraints
- Keep changes minimal and consistent with existing Astro + Vue patterns.
- Do not introduce new dependencies.
- Avoid touching backend code; this set is frontend-only.

