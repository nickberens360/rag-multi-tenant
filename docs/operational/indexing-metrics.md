# Indexing Metrics & Quick Usage

This guide shows how to run indexing with minimal setup and see LLM usage metrics.

## What You Get
- Per‑file LLM classification reused across chunks (Phase 1).
- Optional mixed‑topic detection with selective per‑chunk fallback (Phase 2).
- Persisted file‑level classification to skip reclassification of unchanged files (Phase 3).

## Quick Run (Index-Only, No Vector Store)

Use the helper CLI to index a directory and print a JSON report:

```
make index-report DIR=public
```

Options:
- `FORCE=1` — re-index even if unchanged (still reuses persisted classification if hash matches)
- `HETERO=1` — enable heterogeneity fallback (per-chunk LLM for mixed-topic files)
- `PERSIST_DIR=backend/.unified_chroma` — set index metadata directory
 - `HETEROGENEITY_FALLBACK_INCLUDE=glob1,glob2` — force per‑chunk LLM for matching paths (e.g., `backend/knowledge/*rag*.md`)

Examples:
- `make index-report DIR=public FORCE=1`
- `make index-report DIR=backend/knowledge HETERO=1`

The output includes:
- `files_processed` and `chunks_generated`
- `llm_classifications_performed` — single LLM call per file when reused
- `llm_classifications_fallback_chunk` — per‑chunk LLM calls when fallback is on

## Reading Persisted Classification

Persisted per-file metadata is stored in `backend/.unified_chroma/index_metadata.json` like:

```json
{
  "path/to/file.md": {
    "hash": "<sha256>",
    "classification": {
      "content_type": "project,technical",
      "topic_confidence": 0.92,
      "content_keywords": "python,...",
      "classification_method": "startup_llm",
      "...": "..."
    }
  }
}
```

On re-index, if the file’s current hash matches the persisted hash, the classifier is not called again.

## Toggle Mixed-Topic Fallback (Optional)

Two ways to enable:
- Env: `ENABLE_HETEROGENEITY_FALLBACK=true`
- CLI flag: `make index-report DIR=... HETERO=1`

Force per-chunk classification for specific files (even when fallback is off):
- Env: `HETEROGENEITY_FALLBACK_INCLUDE=backend/knowledge/*rag*.md,backend/knowledge/resume.json`

This adds per‑chunk LLM calls for files detected as mixed-topic (based on token similarity), improving label precision where needed.

## Troubleshooting
- If you see no files processed, confirm the `DIR` path exists and contains indexable files.
- If you get provider or API errors, set your LLM API keys as usual for the project.
- To reset the persisted metadata, delete `backend/.unified_chroma/index_metadata.json`.
