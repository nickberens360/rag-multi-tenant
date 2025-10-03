---
name: Quick win — Re-enable lint/type/coverage guardrails
about: Restore lightweight guardrails to catch regressions earlier
title: "build(tooling): re-enable flake8/mypy pre-commit and basic coverage"
labels: ["build", "ci", "good first issue"]
assignees: []
---

Summary
- Bring back basic lint/type/coverage feedback while keeping dev flow smooth.

Tasks
- Pre-commit: add `flake8` and `mypy` hooks as non-blocking initially (use `--show-error-codes`, relaxed config in `pyproject.toml`).
- Pytest: enable coverage for `backend/core` via `--cov=backend/core --cov-report=term-missing` (keep thresholds lenient or none initially).
- Document in README/CONTRIBUTING how to run `make lint` and tests locally.

Acceptance Criteria
- Pre-commit runs Black, isort, flake8, and mypy locally.
- `pytest` shows coverage summary; HTML report optional.
- CI passes with added checks.

Notes
- Keep strictness low at first; tighten later.

