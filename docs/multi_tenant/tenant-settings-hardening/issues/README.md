# Multi‑Tenant Issues and Fix Plan (AI‑Digestible)

This directory contains a machine‑readable plan for finishing multi‑tenant correctness across the admin app and API. It is structured so an AI agent can locate code, apply safe, targeted patches, and verify changes.

Contents
- `tasks.yaml` – canonical list of tasks with precise targets, patterns, and validations
- `PROGRESS.yaml` – current status for each task (updated as work completes)
- `CONTEXT.md` – quick human‑readable context and rationale

Conventions
- All code paths are relative to repo root
- Prefer explicit tenant filters in SQL (even with RLS) to prevent leakage under superuser sessions
- Prefer FastAPI dependencies for DB sessions (commit/close + GUC handling)
- Frontend must re‑fetch or clear store slices on `tenant` change; avoid duplicating watchers when store ownership is clearer

How an agent should use this
1) Load `tasks.yaml`
2) For each `pending` item in `PROGRESS.yaml`, follow the `changes` guidance to patch code
3) Run the listed `validations` (grep/ripgrep checks, smoke endpoints) to confirm behavior
4) Update `PROGRESS.yaml` statuses with notes

