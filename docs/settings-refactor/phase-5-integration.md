# Phase 5 — Integration (Short, Sequential)

Agent Prompt (copy/paste to kick off this phase)

"""
You are the Phase 5 (Integration) agent.

Goal: Centrally wire the new diagnostics router and configuration validation behind a feature flag, with zero behavior change by default.

Create your worktree/branch from origin/development:
  git fetch origin
  git worktree add -b chore/settings-integration ../wt-settings-integration origin/development
  cd ../wt-settings-integration
  pre-commit install || true

Reference prior phases:
  # Phase 2 (settings_manifest) should be merged or available
  git fetch origin feat/settings-manifest-validation || true

  # A3 diagnostics should be merged or available
  git fetch origin feat/admin-diagnostics-endpoint || true

Deliverable: PR targeting development titled "chore: integration wiring (phase 5)".
"""

## Objective
- Add env flag `USE_NEW_CONFIG_SYSTEM` (default false) — no behavior change by default.
- Include diagnostics router under `/api/admin`.
- Call `validate_configuration()` at startup (log-only; do not crash prod if missing in this phase).

## Minimal Changes (copy/paste guidance)

1) backend/core/app_factory.py — include diagnostics router
```
# Near other imports
from ..routes import admin_diagnostics  # add

# Under Admin API routes inclusion
app.include_router(admin_diagnostics.router, prefix="/api/admin")
```

2) backend/main.py — call validation during startup (log-only)
```
from .core.config_v2 import AppConfig

USE_NEW = os.getenv("USE_NEW_CONFIG_SYSTEM", "false").lower() in {"1", "true", "yes"}

# before app creation or in lifespan startup
if USE_NEW:
    try:
        from .core.settings_manifest import validate_configuration
        summary = validate_configuration()
        logging.getLogger(__name__).info(
            "Config validation OK (env_checked=%s)", summary.get("env_checked")
        )
    except Exception as e:
        logging.getLogger(__name__).warning("Config validation failed: %s", e)
```

Notes
- Keep the validation non-fatal in this phase; we’ll tighten later after rollout.
- Do not modify runtime precedence — only wiring.

## Acceptance Criteria
- Env flag present; default false results in no behavior change.
- Diagnostics route included and reachable when mounted (once merged).
- Validation runs when flag is true and logs outcome without breaking startup.

## Handoff
Open a PR titled "chore: integration wiring (phase 5)" targeting the development branch.
