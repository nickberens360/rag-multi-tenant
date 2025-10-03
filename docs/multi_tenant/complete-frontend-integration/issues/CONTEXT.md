# Context: Complete Frontend Integration (Astro)

Goal: ensure the Astro frontend properly scopes navigation and rendering to the active tenant and gracefully handles tenant resolution failures.

Current state (relevant)
- Dynamic tenant route exists: `src/pages/[tenant]/index.astro` already uses `Astro.params.tenant`.
- Root page (`src/pages/index.astro`) is not tenant‑aware; it’s a general landing page.
- A Vue composable `src/composables/useTenant.ts` parses tenant from subdomain or path and exposes helpers for switching.

What we want to add (high level)
- A consistent, centralized tenant resolver for Astro requests (middleware) with conservative slug validation.
- A redirection from `/` to a tenant home when a default is known, or a tenant selector when unknown.
- Simple helpers for building tenant‑prefixed links to avoid duplication across pages/components.
- Error boundaries:
  - Server‑side: middleware/page‑level guards to handle invalid/missing slugs with a clear 404 or error page.
  - Client‑side: a small Vue error boundary for tenant‑dependent components.

Non‑goals
- Do not change backend APIs; all work is frontend‑only.
- Do not introduce new dependencies; use native Astro/Vue patterns.

