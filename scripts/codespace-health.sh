#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"
echo "== Docker services =="
if command -v docker >/dev/null 2>&1; then
  docker compose ps || true
fi
echo "== Ports =="
for port in 3000 8000 5432 6379 8181 9090 3001; do
  if command -v lsof >/dev/null 2>&1; then
    lsof -i :$port || true
  fi
done
echo "== Backend health =="
curl -fsS http://localhost:8000/health || true
echo
echo "== Frontend health =="
curl -fsS http://localhost:3000/healthz || true
echo
