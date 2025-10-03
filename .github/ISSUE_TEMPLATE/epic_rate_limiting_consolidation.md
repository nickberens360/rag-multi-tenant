---
name: Epic — Consolidate rate limiting strategy
about: Choose one approach (SlowAPI vs custom) with shared storage and remove overlap
title: "epic(rate-limiting): consolidate strategy and storage"
labels: ["epic", "backend", "performance", "security"]
assignees: []
---

Problem
- Two mechanisms exist: SlowAPI limiter and custom in-memory middleware. Overlap causes confusion and env-specific behavior.

Goals
- Single, well-documented strategy with shared storage (Redis or equivalent) in prod; memory in dev/tests.
- Centralized config via settings; consistent bypass rules (e.g., admin routes).

Deliverables
- Remove unused path (either SlowAPI or custom) and related code.
- Tests for rate-limit behavior and admin bypass.
- Operational docs for configuring storage and limits.

