# Phase 2 — Incremental Migration (Weeks 3–8)

Agent Prompt (copy/paste to kick off this phase)

"""
You are the Phase 2 (Incremental Migration) agent.

Goal: Add a centralized settings manifest with validation and tests, without changing runtime behavior or touching integration points. Do not modify backend/main.py or app wiring in this phase.

Create your own worktree/branch from origin/development and then follow the steps in this doc:

- Branch: feat/settings-manifest-validation
- Worktree path: ../wt-settings-manifest

Shell commands:
  git fetch origin
  git worktree add -b feat/settings-manifest-validation ../wt-settings-manifest origin/development
  cd ../wt-settings-manifest
  pre-commit install || true

Reference Phase 1 inventory (for names and classification):
  # If Phase 1 is merged:
  ls docs/reports/settings-inventory.*

  # If Phase 1 is not yet merged, fetch from its branch without switching:
  git fetch origin chore/settings-inventory || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.json > /tmp/settings-inventory.json || true
  git show origin/chore/settings-inventory:docs/reports/settings-inventory.md > /tmp/settings-inventory.md || true

Then implement backend/core/settings_manifest.py and tests/test_settings_manifest.py exactly as specified below. Keep changes isolated to new files. When done, open a PR targeting the development branch titled: "feat: settings manifest + validation (phase 2)".
"""

## Objective
Introduce a centralized settings manifest, validation utilities, a diagnostics endpoint (A3 handles code), and a feature flag — without changing runtime behavior yet.

## Prerequisites
- Repo up to date with `origin/development`
- pytest configured (`pytest -q`)
- Do not edit integration points; Phase 5 (Integration) will wire things up later

## Worktree & Branch
```
# From repo root
git fetch origin
git worktree add -b feat/settings-manifest-validation ../wt-settings-manifest origin/development
cd ../wt-settings-manifest
pre-commit install || true
```

## Files To Add
- backend/core/settings_manifest.py (new)
- tests/test_settings_manifest.py (new)

## settings_manifest.py (copy/paste skeleton)
```
# backend/core/settings_manifest.py
from __future__ import annotations
import os
from typing import Any, Dict

# Admin-managed settings (15-ish curated keys)
ADMIN_MANAGED_SETTINGS: Dict[str, Dict[str, Any]] = {
    'anthropic_api_key': {'type': 'encrypted', 'category': 'api_keys'},
    'google_api_key': {'type': 'encrypted', 'category': 'api_keys'},
    'openai_api_key': {'type': 'encrypted', 'category': 'api_keys', 'optional': True},

    'primary_llm': {'type': 'choice', 'choices': ['claude', 'gemini'], 'category': 'models'},
    'claude_model': {'type': 'str', 'category': 'models'},
    'gemini_model': {'type': 'str', 'category': 'models'},

    'max_results': {'type': 'int', 'min': 5, 'max': 50, 'category': 'performance'},
    'cache_ttl': {'type': 'int', 'min': 60, 'max': 86400, 'category': 'performance'},
    'enable_caching': {'type': 'bool', 'category': 'performance'},

    'enable_rate_limiting': {'type': 'bool', 'category': 'security'},
    'rate_limit_requests': {'type': 'int', 'min': 1, 'max': 10000, 'category': 'security'},
    'rate_limit_window': {'type': 'int', 'min': 1, 'max': 3600, 'category': 'security'},
    'rate_limit': {'type': 'str', 'category': 'security'},

    'search_threshold': {'type': 'int', 'min': 0, 'max': 100, 'category': 'search'},
    'retrieval_score_threshold': {'type': 'float', 'min': 0.1, 'max': 0.9, 'category': 'search'},
}

# Env-only infrastructure and security settings
ENV_ONLY_SETTINGS: Dict[str, Dict[str, Any]] = {
    'ENVIRONMENT': {'type': 'str', 'required': True, 'default': 'development'},
    'API_KEY_ENCRYPTION_SECRET': {'type': 'secret', 'required': True},
    'IP_HASH_SALT': {'type': 'secret', 'required': True},
    'CORS_ORIGINS': {'type': 'str', 'required': False},

    'EMBEDDING_MODEL': {'type': 'str', 'required': True, 'default': 'models/embedding-001'},
    'RAILWAY_VOLUME_MOUNT_PATH': {'type': 'str', 'required': False},
    'SQLITE_JOURNAL_MODE': {'type': 'str', 'required': False, 'default': 'WAL'},

    'LOG_LEVEL': {'type': 'str', 'required': False, 'default': 'INFO'},
    'REQUEST_TIMEOUT': {'type': 'int', 'required': False, 'default': 60},
    'ENABLE_SMART_MODEL_SELECTION': {'type': 'bool', 'required': False, 'default': True},
    'ENABLE_FOLLOWUP_PREGENERATION': {'type': 'bool', 'required': False, 'default': False},
    'CONTENT_CLASSIFICATION_MODE': {'type': 'choice', 'choices': ['fast', 'startup_llm', 'hybrid'], 'default': 'hybrid'},

    'KNOWLEDGE_SYNC_INTERVAL_SECONDS': {'type': 'int', 'required': False, 'default': 0},
    'KNOWLEDGE_SYNC_AUTO_RECONCILE': {'type': 'bool', 'required': False, 'default': False},

    'ADMIN_DEFAULT_USERNAME': {'type': 'str', 'required': False, 'default': 'admin'},
    'ADMIN_DEFAULT_PASSWORD': {'type': 'secret', 'required': True},

    'EXCLUDED_IPS': {'type': 'str', 'required': False},
    'DEBUG': {'type': 'bool', 'required': False, 'default': False},
}

# Explicit env↔DB name mapping for overlapping concepts
ENV_DB_NAME_MAP: Dict[str, str] = {
    'PRIMARY_LLM': 'primary_llm',
    'CLAUDE_MODEL': 'claude_model',
    'GEMINI_MODEL': 'gemini_model',
    'MAX_RESULTS': 'max_results',
    'CACHE_TTL': 'cache_ttl',
    'ENABLE_CACHING': 'enable_caching',
    'RATE_LIMIT': 'rate_limit',
}

class ConfigurationError(Exception):
    pass


def validate_configuration() -> Dict[str, Any]:
    """Validate env-only settings and return a summary dict.

    Raises ConfigurationError on missing required envs.
    """
    errors = []
    summary = {'env_checked': 0, 'missing': []}

    for key, spec in ENV_ONLY_SETTINGS.items():
        required = bool(spec.get('required'))
        if required and not os.getenv(key):
            errors.append(f"Missing required env var: {key}")
            summary['missing'].append(key)
        summary['env_checked'] += 1

    if errors:
        raise ConfigurationError("\n".join(errors))

    return summary
```

## tests/test_settings_manifest.py (copy/paste skeleton)
```
# tests/test_settings_manifest.py
import importlib
import pytest


def test_validate_configuration_missing_required(monkeypatch):
    sm = importlib.import_module('backend.core.settings_manifest')
    # Find at least one required env key
    required_keys = [k for k, v in sm.ENV_ONLY_SETTINGS.items() if v.get('required')]
    assert required_keys, 'Expected at least one required env key'
    # Clear them
    for k in required_keys:
        monkeypatch.delenv(k, raising=False)
    # Expect failure
    with pytest.raises(sm.ConfigurationError):
        sm.validate_configuration()


def test_env_db_name_map_is_consistent():
    sm = importlib.import_module('backend.core.settings_manifest')
    for env_key, db_key in sm.ENV_DB_NAME_MAP.items():
        assert env_key.isupper()
        assert db_key.islower()
```

## Run Tests
```
pytest -q
```

## Acceptance Criteria
- settings_manifest.py present with lists + mapping + validation
- tests added and passing locally
- No changes to backend/main.py or app wiring

## Handoff
Open a PR titled “feat: settings manifest + validation (phase 2)”.
