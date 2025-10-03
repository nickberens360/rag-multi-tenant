# Phase 6 — Tests & CI Hardening (Parallel/Ongoing)

Agent Prompt (copy/paste to kick off this phase)

"""
You are the Phase 6 (Tests & CI Hardening) agent.

Goal: Strengthen tests around the new settings manifest, validation, and diagnostics endpoint. No production code edits; tests only.

Create your worktree/branch from origin/development:
  git fetch origin
  git worktree add -b chore/settings-tests-ci ../wt-settings-tests origin/development
  cd ../wt-settings-tests
  pre-commit install || true

Reference prior phases if not merged:
  git fetch origin feat/settings-manifest-validation || true
  git fetch origin feat/admin-diagnostics-endpoint || true

Deliverable: PR targeting development titled "chore: tests & CI hardening (phase 6)".
"""

## Objective
- Add/extend unit tests for settings manifest validation and diagnostics endpoint.
- Ensure no secrets are returned/logged by diagnostics.
- Keep or improve coverage; ensure pytest passes locally and in CI.

## Suggested Tests
- tests/test_settings_manifest.py
  - Missing required env → raises ConfigurationError
  - ENV_DB_NAME_MAP correctness
- tests/test_admin_diagnostics.py
  - Response shape checks
  - Presence-only markers (no secret values) assertions
  - Health flips to ERROR when required envs are unset (use monkeypatch)

## Commands
```
pytest -q
```

## Acceptance Criteria
- New/updated tests pass locally
- CI passes with stable or improved coverage
- No production code changes in this phase

## Handoff
Open a PR titled "chore: tests & CI hardening (phase 6)" targeting the development branch.
