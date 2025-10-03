---
name: Epic — Modularize admin database layer
about: Split monolithic admin_database.py into cohesive modules with tests
title: "epic(admin-db): split into sessions/users/analytics/rate-limits"
labels: ["epic", "backend", "refactor"]
assignees: []
---

Problem
- `backend/core/admin_database.py` is large and multi-purpose, hindering maintainability and testing.

Goals
- Extract cohesive modules: `sessions.py`, `users.py`, `analytics.py`, `rate_limits.py` under `backend/core/admin_db/`.
- Public interface preserved via a facade or `__init__.py`.

Deliverables
- New modules with unit tests per concern.
- Updated imports across routes/services.
- Migration guide in docs for any public API changes.

