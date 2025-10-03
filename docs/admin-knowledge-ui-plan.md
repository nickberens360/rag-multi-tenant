# Admin Knowledge UI Improvements (Draft)

This document outlines UI changes to visualize and repair knowledge base consistency.

## New: Consistency View

- Summary cards: Filesystem files, Vector docs (chunks), Tracked files, Mismatch counts
- Tables:
  - Discovered but not indexed (FS-only) — actions: Reindex selected
  - Changed files — actions: Reindex selected
  - Vector orphans — actions: Remove selected (requires allow-deletes)
- Reconcile panel:
  - Dry run toggle (default on)
  - Allow deletes toggle (off by default)
  - Optional path filter (comma-separated)
  - Run button shows a summary report

API Wiring:
- GET `/api/admin/knowledge/consistency`
- POST `/api/admin/knowledge/reconcile`

## Enhance: Sources View

- Use enriched `GET /api/admin/knowledge/files/status` instead of raw vector query
- Columns:
  - Path, Status, Ext, Size, mtime, Chunk Count, Vector Count
  - Actions: View/Edit (text files), Reindex, Delete from index (allow-deletes)
- Keep upload/edit modal as-is; backend now updates DB on save

## Enhance: Documents View

- Light tweak: show status badge (indexed/error) based on `metadata` or `/knowledge/files` lookup

## Notifications

- Use existing global toasts for success/error summaries from reconcile actions

## UX Notes

- Prevent destructive actions unless `allow_deletes` is enabled
- For large diffs, paginate table results; provide counts + sample rows
