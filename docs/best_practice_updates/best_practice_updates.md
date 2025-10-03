# RAG Backend Best‑Practice Review — Findings and Updates

_Last updated: 2025-09-05_

## Summary
This document captures an audit of the current Retrieval‑Augmented Generation (RAG) backend. It highlights strengths, best‑practice gaps, and concrete, low‑risk improvements. No code changes were made as part of this review.

## Quick, Low‑Lift Wins
- Enable MMR retrieval as an opt‑in (`search_type="mmr"`) with env‑driven `k/fetch_k/lambda_mult`; fall back to similarity if unsupported.
- Include chat history, model, and salient settings in cache keys to avoid stale/misaligned retrieval and responses.
- Enrich chunk metadata with `chunk_index`, `chunk_size`, `file_hash`, and where possible `page`/`section_title`.
- Add heading‑aware splitters for Markdown/HTML; add PDF page metadata.
- Use deterministic chunk IDs and delete‑before‑upsert for changed/removed files.
- Add an optional source‑aware document prompt so answers can show citations/anchors.

---

## Indexing & Chunking
- Fixed‑size, char‑based splitters: Current splitters are not token‑aware and do not consider model context windows. Recommended to make chunk sizes token‑aware and configurable via env; shrink when `k * chunk_tokens` exceeds context window.
- Structure‑unaware splits: Markdown/HTML not split by headings/sections; PDFs do not preserve `page`. Recommended heading‑aware splitting and preservation of structural metadata (`section_title`, `header_path`, `page`).
- No semantic/anchor chunking: Only naive char splits; risks incoherent fragments. Recommended optional sentence/semantic boundary profile for long narrative content.
- Document context not used at ingest: Helpers exist to create/attach a concise document summary, but `process_directory` does not apply them. Recommended to generate once per file and prepend to chunks to improve grounding.

## Metadata Hygiene
- Strengths: `source` (loader), `file_path`, `file_name`, `file_type`, `content_types`, `content_length`, `has_code`.
- Gaps: No `source_id` (hash of path), `file_hash`, `chunk_index`, `chunk_size`, `profile`, `mtime`. Recommended to add for safe upserts, drift detection, and auditability.
- Missing anchors: Lack of `section_title` and anchor metadata limits cite‑ability and precision. Recommended to enrich during heading‑aware splitting.

## Vector Store & Upserts
- Deterministic IDs: Currently rely on store‑generated IDs; duplicates can accumulate after reindexing. Recommended deterministic IDs per chunk, e.g., `hash8-p{page}-c{idx}`.
- Delete hygiene: Directory indexing doesn’t delete previous vectors for changed/missing files. Recommended delete‑before‑upsert on change/removal by `source` or tracked IDs; add orphan cleanup on startup.
- Distance vs similarity semantics: Chroma returns distance (lower is better). Filtering in code uses `<= threshold` (correct for distance), but config naming references “similarity,” which can confuse tuning. Recommended to align naming/docs or normalize to similarity.

## Retrieval, Diversity & Compression
- Single‑vector similarity: No BM25/hybrid yet. Keep metadata clean to enable future hybrid/ensemble.
- No MMR/diversity: Default retriever risks redundant chunks. Recommended optional MMR with env‑driven params and graceful fallback.
- No context compression/rerank: Consider EmbeddingsFilter + LongContextReorder (or lightweight LLM extractor) and an optional cross‑encoder/hosted reranker for tighter top‑k ordering.

## Prompting & Generation
- Grounding: System prompt instructs grounded answers (“use context or say you don’t know”) — good. Add a `document_prompt` that formats doc snippets with source metadata to support citations.
- History handling: History‑aware reformulation is used on fallback path; ensure cache keys incorporate history when reformulation is active.

## Caching
- Keys too narrow: Cache key is based on normalized `user_input` only; ignores chat history, user/session, model, and settings. This can return stale or mis‑scoped results. Recommended to include history hash length, model, and salient settings, with optional per‑session namespace.
- Memory‑only caches: Fine for single process; consider TTL/size tuning and optional shared cache for horizontal scaling.

## Observability & Evaluation
- Logging & rate‑limit visibility: Present and useful.
- RAG eval: Benchmarks and docs exist, but there’s no automated regression guard in tests for retrieval precision/diversity. Recommended small deterministic tests (recall@k, redundancy under MMR, threshold correctness) with mocked embeddings/search.

## Configuration & Operations
- Hardcoded directories & sizes: Index directories and chunk sizes are hardcoded. Recommended env or `rag.config` (YAML) for dirs, chunk profiles, retrieval params, and thresholds.
- Reindex policy: `index_metadata.json` tracks per‑file hash — good. Add a manifest (`embedding_model`, `dim`, `collection_name`, `created_at`) and force rebuild on embedding model change.
- Deletions/offline cleanup: Add a startup sweep to remove vectors for files that no longer exist when deletion is enabled.

## Security & Safety
- Input validation/sanitization: Present — good.
- Metadata exposure: Absolute `file_path` is included in metadata; typically fine for internal use. For user‑facing citations, consider mapping to logical sources and hiding system paths.

## Tests — Gaps to Close
- Helpers vs reality: Tests cover context helpers, but the ingest pipeline doesn’t apply them. Add an integration test around `process_directory` to verify:
  - Metadata enrichment (`file_hash`, `chunk_index`, `chunk_size`, `page/section_title` when enabled)
  - Deterministic IDs and delete‑before‑upsert behavior
  - Retrieval threshold behavior (distance filter) and MMR when enabled

## Suggested Env Flags (for safe, incremental rollout)
- `RAG_USE_MMR` (bool, default `false`): enable MMR (`k/fetch_k/lambda_mult`).
- `RAG_SCORE_THRESHOLD` (float, default `0.2`): distance cutoff (lower is better); clamp and log.
- `RAG_INDEX_DIRS` (CSV, default `backend/knowledge,public`): directories to index.
- `RAG_USE_HEADING_SPLITTER` (bool, default `false`): enable heading‑aware splitting for MD/HTML.
- `RAG_CHUNK_*` per ext: e.g., `RAG_CHUNK_PDF=1200:200`, `RAG_CHUNK_MD=800:120`, `RAG_CHUNK_HTML=1000:150`.
- `RAG_ENABLE_DELETE` / `RAG_SAFE_DELETE` (bool, default `false`/`true`): deletion behavior.

## Next Steps
1) Implement MMR as a feature‑flagged retriever option with env‑driven params.
2) Expand cache keys to incorporate chat history, model, and salient settings.
3) Add heading‑aware splitters (MD/HTML) and PDF page metadata; enrich chunk metadata accordingly.
4) Adopt deterministic IDs and delete‑before‑upsert; add startup orphan cleanup.
5) Add optional document prompt with source formatting for citations.
6) Add minimal RAG regression tests (recall@k, redundancy, threshold) using mocks.

> All recommendations are designed to be incremental, config‑driven, and low‑risk to adopt.

