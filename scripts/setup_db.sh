#!/usr/bin/env bash
set -euo pipefail

# Simple helper to create a venv, install deps, run Alembic migrations,
# and optionally seed tenants using the repo's .env values.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

echo "[setup-db] Using repository root: $ROOT_DIR"

PYTHON_BIN=${PYTHON_BIN:-python3}

if [ ! -d .venv ]; then
  echo "[setup-db] Creating virtualenv at .venv"
  $PYTHON_BIN -m venv .venv
fi

echo "[setup-db] Activating virtualenv"
source .venv/bin/activate

echo "[setup-db] Upgrading pip and installing backend requirements"
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

# Load environment from .env if present
if [ -f .env ]; then
  echo "[setup-db] Loading .env for DATABASE_URL and tenant defaults"
  # Export only the variables we care about
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^(DATABASE_URL|DEFAULT_TENANT_ID|DEFAULT_TENANT_SLUG|ENABLE_MULTI_TENANT)=' .env | sed 's/^/export /')
  set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "[setup-db] ERROR: DATABASE_URL is not set. Export it or add it to .env"
  echo "Example: export DATABASE_URL=postgresql://user:pass@localhost:5432/app_db"
  exit 1
fi

echo "[setup-db] Running Alembic migrations against DATABASE_URL"
pushd backend >/dev/null
if [ -n "${DATABASE_URL:-}" ]; then
  # Sanitize
  DATABASE_URL=$(printf "%s" "$DATABASE_URL" \
    | tr -d '\r' \
    | sed -e 's/^[[:space:]]*//' \
          -e 's/[[:space:]]*$//' \
          -e 's/^"//' -e 's/"$//' \
          -e "s/^'//" -e "s/'$//")
fi
DATABASE_URL="$DATABASE_URL" ../.venv/bin/alembic -c db/alembic.ini upgrade heads
popd >/dev/null

if [[ "${1:-}" == "--seed" ]]; then
  echo "[setup-db] Seeding tenants via backend/scripts/seed_db.py"
  python backend/scripts/seed_db.py || true
fi

echo "[setup-db] ✅ Completed migrations${1:+ and seeds}."
