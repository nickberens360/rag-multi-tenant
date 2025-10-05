# Document Metadata: User-Defined With LLM Fallback (Multi‑Tenant)

Goal
- Allow admins to set document‑level metadata (e.g., content type, tags) at upload and edit time.
- When metadata is omitted, infer it asynchronously with an LLM and mark provenance as "inferred" with confidence.
- Ensure tenant isolation, auditable overrides, and retrieval that treats manual metadata as authoritative and inferred as hints.

Principles
- Manual > inferred: user input always wins; inference never overwrites manual fields.
- Tenant‑scoped vocabulary: categories/tags are configured per tenant (controlled vocabulary; optional synonyms).
- Asynchronous inference: uploads remain fast; inference runs in background with progress.
- Provenance + confidence: every field carries who/what/when and confidence where applicable.
- Safe retrieval use: inferred metadata is a soft signal (re‑rank), not a hard filter, unless explicitly requested.

Scope (MVP)
- Content type (single select) and optional tags (multi‑select), per file/source.
- UI support in upload dialog and source editor.
- Backend endpoints to accept manual metadata and to retrieve/update it.
- Background LLM inference when nothing is provided.

Out of scope (future)
- Per‑chunk overrides (inherit doc‑level by default; can be added later).
- Complex hierarchies or nested taxonomies.
- Cross‑tenant vocabularies or global governance.

Architecture Overview
- DB: Extend knowledge metadata to store manual vs inferred fields and provenance.
- API:
  - Upload accepts optional `metadata` (content_type, tags[]).
  - Edit/update source metadata endpoint (manual overrides).
  - Background task queues inference for missing items; stores inferred + confidence.
  - Read endpoints return `effective_*` (manual if present else inferred) and `provenance`.
- UI:
  - Upload dialog: pick content type/tags; optional "Suggest tags" toggle displays suggestions once available.
  - Sources/SourcesView: show chips with provenance indicators; allow edit.
  - DocumentsView: display effective metadata + provenance.
- Retrieval:
  - Continue to index documents as today; propagate effective metadata to chunk metadata on reindex.
  - Manual labels can be used as filters; inferred used for scoring bias (no hard exclusion by default).

Data Model (proposed additions)
- Table: `knowledge_files` (existing) — add columns:
  - `manual_content_type` TEXT NULL
  - `manual_tags` JSONB NULL DEFAULT '[]'
  - `inferred_content_type` TEXT NULL
  - `inferred_tags` JSONB NULL DEFAULT '[]'
  - `inferred_confidence` REAL NULL
  - `metadata_provenance` TEXT NOT NULL DEFAULT 'inferred'  -- enum: 'manual' | 'inferred' | 'mixed'
  - `metadata_updated_by` UUID NULL
  - `metadata_updated_at` TIMESTAMPTZ NULL
  - `metadata_version` INT NOT NULL DEFAULT 1
  - Computed effective fields are produced in API responses; storage remains normalized.
- Table: `tenant_taxonomy` (new)
  - `tenant_id` UUID, `key` TEXT, `label` TEXT, `synonyms` JSONB[], `active` BOOL, unique(tenant_id,key)

API Changes (high level)
- POST `/api/admin/knowledge/uploads`: accepts optional multipart form fields:
  - `metadata[content_type]`, `metadata[tags]` (CSV or JSON)
  - If absent, queue inference job.
- PUT `/api/admin/knowledge/sources/{source_path}`: accepts `{ manual_content_type?, manual_tags? }`.
- GET `/api/admin/knowledge/sources`: returns `effective_content_type`, `effective_tags`, and `provenance`.
- POST `/api/admin/knowledge/metadata/infer`: admin trigger to (re)infer batches (dry‑run supported).
- GET/PUT `/api/admin/settings/taxonomy`: manage tenant vocabulary.

Inference Pipeline
- Trigger: upload without metadata (or manual clear) queues background task.
- Worker: reads file content (first N KB + summary), calls LLM, maps to tenant vocabulary; stores `inferred_*` + `confidence`.
- Propagation: on successful inference or manual update, mark file for reindex to stamp chunk metadata with effective values.

Retrieval Semantics
- `effective_*` = manual if present else inferred.
- Manual labels: eligible for strict filter.
- Inferred labels: default to soft reranking; strict filter only when caller opts in (e.g., query param `filter_source=content_type:technical:strict`).

Security & Isolation
- All CRUD is tenant‑scoped via RLS and middleware; taxonomy is per‑tenant.
- Audit: store `metadata_updated_by` and log to audit trail on manual edits.

Rollout Plan
1) Add DB migrations; deploy without UI exposure.
2) Implement backend endpoints + background tasks.
3) Add UI fields (hidden behind feature flag per tenant).
4) Enable for a pilot tenant; validate accuracy/latency/UX.
5) Backfill inference for existing files (job + progress).
6) Gradually enable cross tenants; monitor telemetry.

Risks & Mitigations
- Mis‑tags harm recall → inferred used as soft signal; manual overrides win.
- Tenant vocab drift → make taxonomy manageable in admin with simple analytics.
- Upload latency → inference is async; queue with status API.

Testing Strategy
- Unit: precedence (manual > inferred), mapping to allowed set, RBAC.
- Integration: tenant isolation, upload+infer flow, reindex propagation, retrieval behavior.
- E2E: upload with/without metadata; edit; verify chips + search behavior.

See `document_metadata_tasks.yaml` for machine‑readable steps.

