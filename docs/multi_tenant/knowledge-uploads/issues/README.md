# Multi‑Tenant Knowledge Uploads (Single Store) — AI‑Digestible Plan

This docs package defines a precise, machine‑readable plan to implement tenant‑aware knowledge uploads and retrieval using a single Chroma collection with strict `tenant_id` metadata filtering. It is designed for an agent to make safe, targeted changes with clear validations.

Contents
- `tasks.yaml` – canonical task list with targets, patterns, and validations
- `PROGRESS.yaml` – current status (edit as tasks complete)
- `CONTEXT.md` – current state, goals, constraints

Conventions
- All paths are relative to repo root
- Always add `tenant_id` (UUID string) to vector metadata and filter on it for reads/writes
- For Postgres, use explicit tenant filters in addition to RLS
- Tenant context is derived server‑side (middleware) — do not trust client headers

Agent flow
1) Load `tasks.yaml`
2) For each `pending` item in `PROGRESS.yaml`, apply the prescribed edits
3) Run `validations` (grep/ripgrep checks, smoke tests)
4) Update `PROGRESS.yaml` with statuses and brief notes

