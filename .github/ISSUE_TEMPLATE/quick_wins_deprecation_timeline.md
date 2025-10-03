---
name: Quick win — Document and enforce deprecation timeline
about: Clarify removal date for legacy routes and align headers/docs
title: "docs(routing): finalize deprecation timeline and headers"
labels: ["docs", "backend", "routing", "good first issue"]
assignees: []
---

Summary
- Add a clear removal date for legacy routes and ensure deprecation headers link to the right doc section.

Tasks
- Update `docs/api-routing-standardization-plan.md` with a specific EOL date for:
  - `/api/public/*` aliases
  - legacy root endpoints (`/`, `/status`, `/health`, `/rate-limits`, `/db-paths`, `/welcome-questions`, `/query`, `/default-model`)
- Ensure the `Deprecation` and `Link` headers in `backend/core/app_factory.py` reference the precise section anchor.
- Add a reminder TODO in the doc for the removal window and planned release tag.

Acceptance Criteria
- Doc updated with dates and anchors.
- Deprecation headers correctly reference the updated doc link.
- One tracking issue created for “Remove legacy aliases after EOL”.

