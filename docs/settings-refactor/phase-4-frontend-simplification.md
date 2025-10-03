# Phase 4 — Frontend Simplification (Weeks 13–16)

Agent Prompt (copy/paste to kick off this phase)

"""
You are the Phase 4 (Frontend Simplification) agent.

Goal: Introduce feature flags to hide infra/advanced settings in the admin UI without changing routes. Keep edits minimal and localized.

Create your own worktree/branch from origin/development and then follow the steps in this doc:

- Branch: feat/admin-settings-simplify-flag
- Worktree path: ../wt-admin-simplify

Shell commands:
  git fetch origin
  git worktree add -b feat/admin-settings-simplify-flag ../wt-admin-simplify origin/development
  cd ../wt-admin-simplify
  pre-commit install || true

Reference Phase 1 inventory (to know which settings are env-only):
  # If Phase 1 is merged:
  ls docs/reports/settings-inventory.*

  # If Phase 1 is not yet merged, fetch from its branch without switching:
  git fetch origin chore/settings-inventory || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.json > /tmp/settings-inventory.json || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.md > /tmp/settings-inventory.md || true

Then add admin/frontend/src/config/featureFlags.ts and apply minimal v-if guards as shown below. Build locally to verify. When done, open a PR targeting the development branch titled: "feat: admin settings simplify via flags (phase 4)".
"""

## Objective
Hide/remove admin UI for environment-only settings, preserving the SPA routing. Use feature flags first to avoid router churn; handle removals after cutover.

## Prerequisites
- Repo up to date with `origin/development`
- Node/npm tooling installed
- Do not remove routes yet (flagged hiding only in this phase)

## Worktree & Branch
```
# From repo root
git fetch origin
git worktree add -b feat/admin-settings-simplify-flag ../wt-admin-simplify origin/development
cd ../wt-admin-simplify
pre-commit install || true
```

## Files To Add / Edit (minimally)
- New: `admin/frontend/src/config/featureFlags.ts`
- Minimal v-if guards in relevant settings views (do not touch router yet)

## featureFlags.ts (copy/paste)
```
// admin/frontend/src/config/featureFlags.ts
export default {
  ADMIN_HIDE_INFRA_SETTINGS: false,
}
```

## Usage Example (copy/paste pattern)
In a settings view that currently shows infrastructure/advanced settings:

```
<script setup>
import flags from '@/config/featureFlags'
// ...
</script>

<template>
  <!-- Existing content -->
  <section v-if="!flags.ADMIN_HIDE_INFRA_SETTINGS">
    <!-- Infra/advanced settings UI -->
  </section>
</template>
```

Apply this pattern to views that expose:
- Database/infrastructure paths
- Chunking/embedding parameters
- System-level toggles meant to be env-only

## Build Locally
```
cd admin/frontend
npm run build
```

## Acceptance Criteria
- Infra/advanced settings sections hidden when `ADMIN_HIDE_INFRA_SETTINGS` is true
- No router changes; SPA still served under `/admin`; settings under `/admin/settings`
- Build succeeds locally

## Handoff
Open a PR titled “feat: admin settings simplify via flags (phase 4)”.
