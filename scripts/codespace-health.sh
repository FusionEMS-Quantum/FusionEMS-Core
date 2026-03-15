#!/usr/bin/env bash
# FusionEMS-Core — Codespace Health Check
# Returns structured health status for all local services.
# Exit 0 = all healthy, Exit 1 = degraded.
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

PASS=0
FAIL=0
WARN=0

check() {
  local name="$1" cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  [PASS] $name"
    ((PASS++))
  else
    echo "  [FAIL] $name"
    ((FAIL++))
  fi
}

warn_check() {
  local name="$1" cmd="$2"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  [PASS] $name"
    ((PASS++))
  else
    echo "  [WARN] $name (non-critical)"
    ((WARN++))
  fi
}

echo "======================================"
echo " FusionEMS-Core Health Check"
echo "======================================"

echo ""
echo "== Infrastructure =="
check "Docker available" "command -v docker"
warn_check "Docker Compose running" "docker compose ps --quiet 2>/dev/null"
check "ripgrep available" "command -v rg"
check "bubblewrap available" "command -v bwrap"
check "socat available" "command -v socat"

echo ""
echo "== Ports =="
for port in 5432 6379 8000 3000; do
  warn_check "Port $port listening" "lsof -i :$port -sTCP:LISTEN"
done

echo ""
echo "== Backend =="
check "Python venv exists" "test -f .venv/bin/python"
check "Backend package importable from repo root" "PYTHONPATH=$ROOT_DIR/backend .venv/bin/python -c 'import core_app.main' 2>/dev/null"
check "Backend package importable from backend cwd" "cd backend && ../.venv/bin/python -c 'import core_app.main' 2>/dev/null"
warn_check "Backend /health OK" "curl -fsS --max-time 5 http://localhost:8000/health"

echo ""
echo "== Frontend =="
warn_check "node_modules exists" "test -d frontend/node_modules"
warn_check "Frontend healthz OK" "curl -fsS --max-time 5 http://localhost:3000"

echo ""
echo "======================================"
echo " Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "======================================"

if [ "$FAIL" -gt 0 ]; then
  echo " STATUS: DEGRADED"
  exit 1
else
  echo " STATUS: HEALTHY"
  exit 0
fi
