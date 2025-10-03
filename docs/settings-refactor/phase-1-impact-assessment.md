# Phase 1 — Impact Assessment (Weeks 1–2)

Agent Prompt (copy/paste to kick off this phase)

"""
You are the Phase 1 (Impact Assessment) agent.

Goal: Build a complete inventory of all settings (env, DB/admin, code defaults) and classify each as admin‑managed or env‑only without changing app behavior.

Create your own worktree/branch from origin/development and then follow the steps in this doc:

- Branch: chore/settings-inventory
- Worktree path: ../wt-settings-inventory

Shell commands:
  git fetch origin
  git worktree add -b chore/settings-inventory ../wt-settings-inventory origin/development
  cd ../wt-settings-inventory
  pre-commit install || true

Then execute the Discovery Commands and produce the Inventory Artifacts exactly as specified below. Do not modify application code in this phase. When done, open a PR targeting the development branch titled: "chore: settings inventory (phase 1)" and include links to the generated artifacts.
"""

## Objective
Build a complete inventory of all settings (env, DB/admin, code defaults) and where they’re used. Classify each as admin‑managed vs env‑only per the refactor plan, without changing app behavior.

## Prerequisites
- Repo up to date with `origin/development`
- ripgrep installed (`rg`)
- Python + pytest available (no code changes in this phase)

## Worktree & Branch
Copy/paste to create an isolated workspace:

```
# From repo root
git fetch origin
git worktree add -b chore/settings-inventory ../wt-settings-inventory origin/development
cd ../wt-settings-inventory
pre-commit install || true
```

## Discovery Commands
Create a reports folder and capture scans:

```
mkdir -p docs/reports

# 1) Environment variable reads
rg -n "os.getenv\(" backend | tee docs/reports/scan_env_vars.txt

# 2) Central config usage (AppConfig getters and constants)
rg -n "\bAppConfig\.(get_|[A-Z_]+)" backend | tee docs/reports/scan_appconfig_usage.txt

# 3) Settings manager reads (DB/admin)
rg -n "get_.*_settings\(|get_system_config_settings\(|get_response_settings\(" backend \
  | tee docs/reports/scan_settings_manager.txt

# 4) API key manager usage (secrets handling)
rg -n "api_key_manager|ApiKeyManager" backend | tee docs/reports/scan_api_keys.txt
```

Optional (frontend):
```
rg -n "settings|feature|rate limit|model" admin/frontend/src | tee docs/reports/scan_admin_frontend.txt
```

## Inventory Artifacts
Create the inventory JSON skeleton:

```
cat > docs/reports/settings-inventory.json <<'JSON'
[
  {
    "key_name": "PRIMARY_LLM",
    "source_type": "env|db|code_default",
    "code_refs": ["backend/core/llm_chain.py:72"],
    "sensitive": false,
    "notes": "Mapped to primary_llm; admin-managed"
  }
]
JSON
```

Create the summary markdown:
```
cat > docs/reports/settings-inventory.md <<'MD'
# Settings Inventory Summary

- Total keys found: <fill>
- Proposed admin-managed: <fill>
- Proposed env-only: <fill>
- Unknown/needs review: <fill>

## Notes
- Scaling: search_threshold is 0–100 UI; retrieval_score_threshold is 0.1–0.9.
- Secrets never printed; diagnostics must use presence indicators only.
MD
```

## Classification Rules (from plan)
- DB keys use snake_case; env keys use UPPER_SNAKE_CASE.
- Admin-managed: keys that must change at runtime (models, caching, rate limits, thresholds, API keys managed via DB encryption).
- Env-only: infra, security, platform, and any change requiring reindexing or redeployment.

## Acceptance Criteria
- docs/reports/scan_*.txt generated with non-empty content
- docs/reports/settings-inventory.json present with initial entries
- docs/reports/settings-inventory.md summarizing counts and unknowns
- No app code changes in this phase

## Handoff
Open a PR titled “chore: settings inventory (phase 1)” linking the generated artifacts.
