---
name: Quick win — Replace print() with logging
about: Replace print statements in runtime code with structured logging
title: "chore(logging): replace print() with logging in routes and services"
labels: ["chore", "good first issue", "backend", "observability"]
assignees: []
---

Summary
- Replace print() calls in runtime backend code with `logging` for consistency and better observability.

Scope
- Primary: `backend/routes/health.py` error paths (status/rate-limits/welcome-questions).
- Secondary: scan `backend/**` (exclude `backend/scripts/**`, `backend/knowledge/**`, and tests) for `print(`.

Acceptance Criteria
- No `print()` calls remain in runtime backend code paths (routes/services).
- Errors and exceptions logged via module logger with appropriate level; unexpected exceptions include `exc_info=True`.
- Unit tests pass (`pytest -q`).

Notes
- Keep prints in CLI utilities under `backend/scripts/` and test diagnostics.
- Follow existing logging config from `backend/main.py`.

