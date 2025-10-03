---
name: Epic — DRY knowledge route logic
about: Extract shared service layer for knowledge endpoints and thin routers
title: "epic(knowledge): dedupe logic across public/admin routes"
labels: ["epic", "backend", "routing", "refactor"]
assignees: []
---

Problem
- `backend/routes/knowledge.py` (admin) and `knowledge_public.py` (public) duplicate query/list/read logic.

Goals
- Create `backend/core/knowledge_service.py` (or similar) with shared read/query interfaces.
- Keep routers focused on auth/validation/response models.

Deliverables
- New service module with unit tests.
- Routers refactored to call shared service; behavior preserved.
- Reduced LOC and easier maintenance.

