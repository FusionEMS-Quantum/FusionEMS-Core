#!/usr/bin/env bash
# FusionEMS-Core — ENOPRO workspace/provider doctor
# Focused on diagnosing VS Code / Codespaces workspace-provider failures.
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT_DIR"

PASS=0
WARN=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  [PASS] $1"; }
warn() { WARN=$((WARN + 1)); echo "  [WARN] $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

echo "======================================"
echo " FusionEMS-Core ENOPRO Doctor"
echo "======================================"

echo ""
echo "== Workspace =="
if [ -d "$ROOT_DIR/.git" ]; then
  pass "Repository root reachable"
else
  fail "Repository root not reachable"
fi

if [ -f "$ROOT_DIR/.vscode/settings.json" ]; then
  pass "Workspace settings present"
else
  warn "Workspace settings missing"
fi

echo ""
echo "== Sandbox prerequisites =="
command -v rg >/dev/null 2>&1 && pass "ripgrep available" || fail "ripgrep missing"
command -v bwrap >/dev/null 2>&1 && pass "bubblewrap available" || fail "bubblewrap missing"
command -v socat >/dev/null 2>&1 && pass "socat available" || fail "socat missing"

echo ""
echo "== Python =="
if [ -f .venv/bin/python ]; then
  pass ".venv python present"
else
  fail ".venv/bin/python missing"
fi

if PYTHONPATH="$ROOT_DIR/backend" .venv/bin/python -c 'import core_app.main' >/dev/null 2>&1; then
  pass "Backend importable from repo root"
else
  fail "Backend not importable from repo root"
fi

if (cd backend && ../.venv/bin/python -c 'import core_app.main' >/dev/null 2>&1); then
  pass "Backend importable from backend cwd"
else
  fail "Backend not importable from backend cwd"
fi

echo ""
echo "== Services =="
command -v docker >/dev/null 2>&1 && pass "Docker CLI available" || warn "Docker CLI unavailable"
docker compose ps --quiet >/dev/null 2>&1 && pass "docker compose responds" || warn "docker compose not responding"

echo ""
echo "== Guidance =="
if [ "$FAIL" -gt 0 ]; then
  echo "  Workspace or local dependencies are degraded."
  echo "  1. Reload the VS Code window"
  echo "  2. Reopen /workspaces/FusionEMS-Core"
  echo "  3. Rebuild/restart the dev container or Codespace"
  echo "  4. Re-run bash scripts/codespace-up.sh and bash scripts/codespace-health.sh"
else
  echo "  Local prerequisites look healthy."
  echo "  If ENOPRO still appears, the likely fault is the VS Code/Codespaces file-system provider, not repo code."
fi

echo ""
echo "======================================"
echo " Results: $PASS passed, $FAIL failed, $WARN warnings"
echo "======================================"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi

exit 0