# Frontend Integration Issues and Fix Plan (AI‑Digestible)

This directory contains a machine‑readable plan to finish tenant‑aware frontend integration in the Astro site. It is structured so an AI agent can locate files, apply safe, targeted patches, and verify changes without backend modifications.

Contents
- `tasks.yaml` – canonical list of tasks with precise targets, patterns, and validations
- `PROGRESS.yaml` – current status for each task (updated as work completes)
- `CONTEXT.md` – quick human‑readable context and rationale

Conventions
- All code paths are relative to repo root
- Tenancy resolution precedence: subdomain in production, path prefix in development
- Prefer a central middleware (`src/middleware.ts`) and small utilities for consistency
- Astro pages should reference `Astro.params.tenant` or `Astro.locals.tenantSlug` and generate tenant‑prefixed links via a helper
- For UX, add friendly error handling and not just raw 404s when tenant resolution fails

How an agent should use this
1) Load `tasks.yaml`
2) For each `pending` item in `PROGRESS.yaml`, follow the `changes` guidance to patch code
3) Run the listed `validations` (grep/ripgrep checks, manual smoke) to confirm behavior
4) Update `PROGRESS.yaml` statuses with notes

