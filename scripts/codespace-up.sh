#!/usr/bin/env bash
# FusionEMS-Core — Start Local Infrastructure
# Idempotent: safe to run multiple times.
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "[SKIP] Docker not available — running without infrastructure services"
  exit 0
fi

echo "[1/3] Starting Docker services..."
docker compose up -d postgres redis 2>/dev/null || docker compose up -d 2>/dev/null || {
  echo "[WARN] Docker Compose failed — services may need manual start"
  exit 0
}

echo "[2/3] Waiting for PostgreSQL..."
export DATABASE_URL=${DATABASE_URL:-postgresql+psycopg2://postgres:postgres@localhost:5432/fusionems}
MAX_WAIT=60
WAITED=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
  if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
    echo "  PostgreSQL ready after ${WAITED}s"
    break
  fi
  sleep 2
  WAITED=$((WAITED + 2))
done
if [ "$WAITED" -ge "$MAX_WAIT" ]; then
  echo "  [WARN] PostgreSQL not ready after ${MAX_WAIT}s"
fi

echo "[3/3] Running database migrations..."
if [ -f backend/alembic.ini ]; then
  if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
  fi
  (cd backend && alembic upgrade head 2>/dev/null) || echo "  [WARN] Alembic migrations failed (DB may not be ready)"
fi

echo "Infrastructure startup complete"
