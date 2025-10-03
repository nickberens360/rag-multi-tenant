---
name: Quick win — Repo hygiene cleanup
about: Remove stray/temp files and prevent reintroduction
title: "chore(repo): remove stray files and add hygiene guardrails"
labels: ["chore", "good first issue", "repo hygiene"]
assignees: []
---

Summary
- Remove temporary/backup files and ensure they don’t come back.

Targets
- Delete obvious strays:
  - `backend/core/.!88074!auto_discovery.py` (0 bytes)
  - `backend/core/unified_retriever_old.py` (confirm deprecation, then remove)
  - `src/components/CustomLMGTFY.vue.backup`
  - Any committed `.DS_Store` files
- Verify `.gitignore` covers `.DS_Store` (it does) and backups; add if needed.
- Optionally add a pre-commit hook to block `.DS_Store` and `*.backup` files.

Acceptance Criteria
- Files above removed from repo (if confirmed unused).
- Pre-commit check to prevent `.DS_Store` and `*.backup` files added or confirmed present.
- CI/static checks pass.

Notes
- If `unified_retriever_old.py` is referenced anywhere, open a follow-up refactor issue instead of deleting.

