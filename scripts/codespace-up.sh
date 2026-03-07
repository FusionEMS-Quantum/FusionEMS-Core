#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"
if ! command -v docker >/dev/null 2>&1; then
  echo "docker_not_available"
  exit 0
fi
docker compose up -d postgres redis opa backend frontend
export DATABASE_URL=${DATABASE_URL:-postgresql+psycopg2://postgres:postgres@localhost:5432/fusionems}
if command -v pg_isready >/dev/null 2>&1; then
  for _ in $(seq 1 30); do
    if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi
if [ -f backend/alembic.ini ]; then
  (cd backend && alembic upgrade head) || true
fi
