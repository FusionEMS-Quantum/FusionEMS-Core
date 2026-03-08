#!/usr/bin/env bash
# FusionEMS-Core — Codespace Start Hook
# Runs every time the Codespace starts (resumption included).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== FusionEMS-Core: post-start ==="

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
