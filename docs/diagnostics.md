# Diagnostics (Dev/Ops)

A small diagnostics module helps verify filesystem permissions, resolved database paths, and persistent volume configuration.

## Usage

Run from the repo root:

- Check permissions for `/data` and the Chroma persist dir
  - `python -m backend.tools.diagnostics perms`
- Show resolved SQLite DB paths (via `get_database_path`)
  - `python -m backend.tools.diagnostics db-paths`
- Verify Railway volume mount and writability
  - `python -m backend.tools.diagnostics volume`

## Notes

- No migrations are required; SQLite schemas are created on first use.
- On Railway, ensure a persistent volume is mounted at `/data` and set:
  - `UNIFIED_PERSIST_DIR=/data/unified_chroma`
- The admin API mounts content routes under both `/api` and `/api/admin`.

