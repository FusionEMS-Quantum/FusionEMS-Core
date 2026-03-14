#!/usr/bin/env bash
# FusionEMS-Core — Codespace Start Hook
# Runs every time the Codespace starts (resumption included).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== FusionEMS-Core: post-start ==="

# Ensure required dependencies exist for VS Code terminal sandbox execution.
# This runs on every start so older containers can self-heal after restart.
missing_deps=()
command -v rg >/dev/null 2>&1 || missing_deps+=("ripgrep")
command -v bwrap >/dev/null 2>&1 || missing_deps+=("bubblewrap")
command -v socat >/dev/null 2>&1 || missing_deps+=("socat")

if [ ${#missing_deps[@]} -gt 0 ]; then
  echo "[0/4] Installing required sandbox deps: ${missing_deps[*]}"
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing_deps[@]}"
  else
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing_deps[@]}"
  fi
fi

# Activate venv if present
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

# Start infrastructure services
echo "[1/3] Starting infrastructure services..."
bash scripts/codespace-up.sh || echo "  WARNING: codespace-up.sh failed (Docker may not be available)"

# Run health check
echo "[2/4] Running health check..."
bash scripts/codespace-health.sh || echo "  WARNING: Some health checks failed"

echo "[3/4] Checking migration status..."
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
  (cd backend && alembic current 2>/dev/null) || echo "  WARNING: Could not check migration status (DB may not be ready)"
fi

echo "[4/4] Environment ready"
echo "=== post-start complete ==="
