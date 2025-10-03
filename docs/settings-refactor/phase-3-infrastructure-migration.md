# Phase 3 — Infrastructure Settings Migration (Weeks 9–12)

Agent Prompt (copy/paste to kick off this phase)

"""
You are the Phase 3 (Infrastructure Migration) agent.

Goal: Implement the scripts to migrate infra settings from DB to env, plus Railway env sync and deployment validation scripts. Use dry-run first; do not change runtime precedence.

Create your own worktree/branch from origin/development and then follow the steps in this doc:

- Branch: feat/settings-migration-scripts
- Worktree path: ../wt-settings-migration

Shell commands:
  git fetch origin
  git worktree add -b feat/settings-migration-scripts ../wt-settings-migration origin/development
  cd ../wt-settings-migration
  pre-commit install || true

Reference Phase 1 inventory (for env-only vs admin-managed classification):
  # If Phase 1 is merged:
  ls docs/reports/settings-inventory.*

  # If Phase 1 is not yet merged, fetch from its branch without switching:
  git fetch origin chore/settings-inventory || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.json > /tmp/settings-inventory.json || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.md > /tmp/settings-inventory.md || true

Then add the scripts exactly as specified (backend/scripts/migrate_settings_to_env.py, scripts/sync-environments.sh, scripts/validate-deployment.sh, scripts/required-env.txt). Validate locally with dry-run. When done, open a PR targeting the development branch titled: "feat: infra settings migration scripts (phase 3)".
"""

## Objective
Move infrastructure settings to environment variables, add sync/validation tooling, and enforce precedence under a feature flag — without disrupting production.

## Prerequisites
- Repo up to date with `origin/development`
- Railway CLI + jq installed for env sync
- Dry-run any destructive steps first

## Worktree & Branch
```
# From repo root
git fetch origin
git worktree add -b feat/settings-migration-scripts ../wt-settings-migration origin/development
cd ../wt-settings-migration
pre-commit install || true
```

## Files To Add
- backend/scripts/migrate_settings_to_env.py
- scripts/sync-environments.sh
- scripts/validate-deployment.sh
- scripts/required-env.txt (seed list)

## backend/scripts/migrate_settings_to_env.py (copy/paste skeleton)
```
# backend/scripts/migrate_settings_to_env.py
"""Export infra settings to .env.infrastructure and remove them from DB (optional).
Run with --dry-run to preview changes."""

import argparse
from typing import Dict


def get_all_db_settings() -> Dict[str, str]:
    # Lazy import to avoid runtime deps during packaging
    from backend.core.settings_manager import get_settings_manager

    sm = get_settings_manager()
    return sm.get_all()  # assumes dict[str, Any]


NAME_MAP = {
    'primary_llm': 'PRIMARY_LLM',
    'claude_model': 'CLAUDE_MODEL',
    'gemini_model': 'GEMINI_MODEL',
    'max_results': 'MAX_RESULTS',
    'cache_ttl': 'CACHE_TTL',
    'enable_caching': 'ENABLE_CACHING',
    'rate_limit': 'RATE_LIMIT',
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    from backend.core.settings_manifest import ADMIN_MANAGED_SETTINGS

    all_settings = get_all_db_settings()
    export_lines = []
    delete_keys = []

    for key, value in all_settings.items():
        if key not in ADMIN_MANAGED_SETTINGS:
            env_key = NAME_MAP.get(key, key.upper())
            export_lines.append(f"{env_key}={value}")
            delete_keys.append(key)

    if not export_lines:
        print('No infra settings to export.')
        return 0

    # Write export file
    with open('.env.infrastructure', 'w') as f:
        f.write("\n".join(export_lines) + "\n")
    print(f"Exported {len(export_lines)} env entries to .env.infrastructure")

    if args.dry_run:
        print('[DRY RUN] Skipping DB deletions')
        return 0

    # Remove from DB
    from backend.core.settings_manager import get_settings_manager
    sm = get_settings_manager()
    for k in delete_keys:
        try:
            sm.delete_setting(k)
            print(f"Removed {k} from DB")
        except Exception as e:
            print(f"Warning: failed to delete {k} from DB: {e}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
```

## scripts/sync-environments.sh (copy/paste)
```
#!/usr/bin/env bash
set -euo pipefail

SRC_ENV=${1:-production}
DST_ENV=${2:-development}

echo "Exporting $SRC_ENV variables..."
railway variables --environment "$SRC_ENV" --json > /tmp/src.vars.json

echo "Syncing to $DST_ENV..."
jq -r 'to_entries[] | "\(.key)=\(.value)"' /tmp/src.vars.json | while IFS='=' read -r key value; do
  railway variables set --environment "$DST_ENV" "$key"="$value"
done

echo "Done. Review $DST_ENV variables in the Railway dashboard."
```

## scripts/required-env.txt (seed list)
```
ENVIRONMENT
API_KEY_ENCRYPTION_SECRET
IP_HASH_SALT
EMBEDDING_MODEL
LOG_LEVEL
REQUEST_TIMEOUT
CONTENT_CLASSIFICATION_MODE
ADMIN_DEFAULT_PASSWORD
```

## scripts/validate-deployment.sh (copy/paste)
```
#!/usr/bin/env bash
set -euo pipefail

ENV_NAME=${1:?"Usage: $0 <environment> [required-file]"}
REQUIRED_FILE=${2:-scripts/required-env.txt}

echo "Validating required env keys using $REQUIRED_FILE..."
missing=0
while IFS= read -r key || [ -n "$key" ]; do
  [ -z "$key" ] && continue
  val=$(railway variables --environment "$ENV_NAME" --json | jq -r --arg k "$key" '.[$k] // empty')
  if [ -z "$val" ]; then
    echo "✗ Missing: $key"; missing=$((missing+1))
  else
    echo "✓ Present: $key"
  fi
done < "$REQUIRED_FILE"
if [ $missing -gt 0 ]; then
  echo "❌ Missing $missing required environment variables"; exit 1
fi

# Test critical endpoints (requires $RAILWAY_STATIC_URL exposed in env)
curl -f "https://$RAILWAY_STATIC_URL/health" || exit 1
curl -f "https://$RAILWAY_STATIC_URL/api/admin/diagnostics" || exit 1

echo "✓ Deployment validation passed"
```

## Run Locally (dry-run first)
```
python -m backend.scripts.migrate_settings_to_env --dry-run
```

## Acceptance Criteria
- `.env.infrastructure` generated with env-only exports
- Dry-run shows DB keys to be removed; non-dry-run removes them safely
- Sync + validation scripts present and executable

## Handoff
Open a PR titled “feat: infra settings migration scripts (phase 3)”.
