# A3 — Diagnostics Endpoint (Run in Parallel)

Agent Prompt (copy/paste to kick off this workstream)

"""
You are the A3 (Diagnostics Endpoint) agent.

Goal: Add a new admin diagnostics router that reports configuration presence (no secrets) for env-only and admin-managed settings. Do NOT wire it into the app — the Integration Owner (Phase 5) will include the router in app_factory later.

Create your worktree/branch from origin/development:
  git fetch origin
  git worktree add -b feat/admin-diagnostics-endpoint ../wt-admin-diagnostics origin/development
  cd ../wt-admin-diagnostics
  pre-commit install || true

Reference Phase 1 inventory (since it may not be merged yet):
  git fetch origin chore/settings-inventory || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.json > /tmp/settings-inventory.json || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.md > /tmp/settings-inventory.md || true

Implement exactly as specified below. Keep changes isolated to NEW files. When done, open a PR targeting the development branch titled: "feat: admin diagnostics endpoint (A3)".
"""

## Objective
Provide `/api/admin/diagnostics` that:
- Returns environment: `ENVIRONMENT` or fallback `RAILWAY_ENVIRONMENT`.
- Shows env-only required keys presence (✓/✗), not values.
- Shows admin-managed settings presence from DB (✓/✗), not values.
- Sets `health: OK` if all required envs present, otherwise `ERROR`.
- Never logs or returns secret values.

## Files To Add
- `backend/routes/admin_diagnostics.py` (new)
- `tests/test_admin_diagnostics.py` (new)

## Router (copy/paste skeleton)
```
# backend/routes/admin_diagnostics.py
from __future__ import annotations
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import manifests lazily to avoid circulars in some test contexts
try:
    from backend.core.settings_manifest import ENV_ONLY_SETTINGS, ADMIN_MANAGED_SETTINGS
except Exception:
    ENV_ONLY_SETTINGS = {}
    ADMIN_MANAGED_SETTINGS = {}

router = APIRouter()

@router.get("/api/admin/diagnostics")
async def get_diagnostics():
    env_status = {}
    for key in ENV_ONLY_SETTINGS.keys():
        env_status[key] = "✓" if os.getenv(key) else "✗ MISSING"

    # Best-effort DB check via settings_manager
    admin_status = {}
    try:
        from backend.core.settings_manager import get_settings_manager
        sm = get_settings_manager()
        db_settings = sm.get_all()  # non-sensitive snapshot
        for key in ADMIN_MANAGED_SETTINGS.keys():
            admin_status[key] = "✓" if key in db_settings else "✗ MISSING"
    except Exception:
        for key in ADMIN_MANAGED_SETTINGS.keys():
            admin_status[key] = "✗ MISSING"

    environment = os.getenv("ENVIRONMENT") or os.getenv("RAILWAY_ENVIRONMENT") or "unknown"
    missing_env = [k for k, v in env_status.items() if "MISSING" in v]

    payload = {
        "environment": environment,
        "env_variables": {
            "total": len(env_status),
            "missing": len(missing_env),
            "status": env_status,
        },
        "admin_settings": {
            "total": len(admin_status),
            "configured": sum(1 for v in admin_status.values() if v.startswith("✓")),
            "status": admin_status,
        },
        "health": "ERROR" if missing_env else "OK",
    }
    return JSONResponse(content=payload)
```

## Tests (copy/paste skeleton)
```
# tests/test_admin_diagnostics.py
import json
from importlib import import_module


def test_diagnostics_shape(client):
    # Assume test client fixture named `client` exists; if not, add a local TestClient
    try:
        resp = client.get("/api/admin/diagnostics")
    except Exception:
        # Fallback local client if not provided by test harness
        from fastapi.testclient import TestClient
        app_mod = import_module('backend.main')
        client = TestClient(app_mod.app)
        resp = client.get("/api/admin/diagnostics")

    assert resp.status_code == 200
    data = resp.json()
    assert set(["environment", "env_variables", "admin_settings", "health"]).issubset(data.keys())

    env_section = data["env_variables"]
    assert set(["total", "missing", "status"]).issubset(env_section.keys())
    assert isinstance(env_section["status"], dict)

    admin_section = data["admin_settings"]
    assert set(["total", "configured", "status"]).issubset(admin_section.keys())


def test_diagnostics_no_secrets_in_values(monkeypatch):
    from importlib import import_module
    from fastapi.testclient import TestClient

    app_mod = import_module('backend.main')
    client = TestClient(app_mod.app)
    resp = client.get("/api/admin/diagnostics")
    data = resp.json()

    # Ensure values are presence markers only, not raw values
    for v in data["env_variables"]["status"].values():
        assert v in ("✓", "✗ MISSING")
    for v in data["admin_settings"]["status"].values():
        assert v in ("✓", "✗ MISSING")
```

## Notes
- Do not modify `backend/core/app_factory.py` — Phase 5 will include `admin_diagnostics.router` under `/api/admin`.
- Keep logging minimal; never print env values.

## Run Tests
```
pytest -q
```

## Acceptance Criteria
- New router responds at `/api/admin/diagnostics` with presence-only markers.
- No secrets returned; tests confirm presence markers only.
- No changes to existing modules beyond adding new files.

## Handoff
Open a PR titled “feat: admin diagnostics endpoint (A3)” targeting the development branch.
