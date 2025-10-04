#!/usr/bin/env bash
set -euo pipefail

# One-shot DB setup for local dev with Podman:
# - Creates network 'rag-multi-tenant-network' if missing
# - Starts Postgres container named 'postgres' on that network (or starts it if exists)
# - Waits until DB is ready
# - Creates .venv, installs backend deps (incl. Alembic)
# - Runs Alembic migrations against localhost:5432 (port-forwarded)
# - Optional --seed: seeds default tenants

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

echo "[db:setup] Repo root: $ROOT_DIR"

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "[db:setup] ERROR: Missing required command: $1"; exit 1; }; }

need_cmd podman

# Create network if not present
if ! podman network inspect rag-multi-tenant-network >/dev/null 2>&1; then
  echo "[db:setup] Creating podman network 'rag-multi-tenant-network'"
  podman network create rag-multi-tenant-network >/dev/null
else
  echo "[db:setup] Network 'rag-multi-tenant-network' already exists"
fi

# Start or run the postgres container
if podman inspect postgres >/dev/null 2>&1; then
  state=$(podman inspect -f '{{.State.Status}}' postgres || echo "unknown")
  if [ "$state" != "running" ]; then
    echo "[db:setup] Starting existing 'postgres' container"
    podman start postgres >/dev/null
  else
    echo "[db:setup] 'postgres' container already running"
  fi
else
  echo "[db:setup] Running new 'postgres' container"
  podman run -d --name postgres \
    --network rag-multi-tenant-network \
    -p 5432:5432 \
    -e POSTGRES_DB=app_db \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres_admin_pass \
    -v postgres_data:/var/lib/postgresql/data \
    docker.io/library/postgres:16-alpine >/dev/null
fi

# Wait for readiness
echo -n "[db:setup] Waiting for Postgres to be ready"
for i in $(seq 1 60); do
  if podman exec postgres pg_isready -U postgres -d app_db >/dev/null 2>&1; then
    echo " — ready"
    break
  fi
  echo -n "."; sleep 1
  if [ "$i" = "60" ]; then
    echo "\n[db:setup] ERROR: Postgres did not become ready in time"; exit 1
  fi
done

# Python venv + deps
if [ ! -d .venv ]; then
  echo "[db:setup] Creating .venv"
  python3 -m venv .venv
fi
source .venv/bin/activate
echo "[db:setup] Installing backend requirements"
python -m pip install --upgrade pip >/dev/null
pip install -r backend/requirements.txt >/dev/null

# Determine DATABASE_URL for migration calls
DB_URL=""
if [ -f .env ]; then
  # Extract DATABASE_URL value
  DB_URL=$(grep -E '^DATABASE_URL=' .env | head -n1 | sed 's/^DATABASE_URL=//') || true
fi

if [ -z "$DB_URL" ]; then
  # Fallback to defaults that match the container we run
  DB_URL="postgresql://postgres:postgres_admin_pass@localhost:5432/app_db"
else
  # Override host to localhost for host-side migration
  # Strip quotes/whitespace and CRs
  DB_URL=$(printf "%s" "$DB_URL" \
    | tr -d '\r' \
    | sed -e 's/^[[:space:]]*//' \
          -e 's/[[:space:]]*$//' \
          -e 's/^"//' -e 's/"$//' \
          -e "s/^'//" -e "s/'$//")
  # Replace host '@postgres' with '@localhost' for host-side migrations only
  DB_URL="${DB_URL//@postgres/@localhost}"
fi

echo "[db:setup] Using DB URL for seeds: $(printf "%s" "$DB_URL" | sed -E 's#(postgresql://[^:]+:)[^@]+#\1***#')"
echo "[db:setup] Running Alembic migrations (using alembic.ini URL)"
# Run from backend dir so script_location=db resolves correctly and ignore env URL for migration
pushd backend >/dev/null
env -u DATABASE_URL ../.venv/bin/alembic -c db/alembic.ini upgrade heads
popd >/dev/null

if [[ "${1:-}" == "--seed" ]]; then
  echo "[db:setup] Seeding tenants (DEFAULT_TENANT_* from .env if set)"
  DATABASE_URL="$DB_URL" .venv/bin/python backend/scripts/seed_db.py || true
fi

echo "[db:setup] ✅ DB ready. You can start the backend container:"
echo "           npm run backend:dev"
