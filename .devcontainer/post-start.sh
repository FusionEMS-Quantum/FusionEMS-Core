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
echo "[2/3] Running health check..."
bash scripts/codespace-health.sh || echo "  WARNING: Some health checks failed"

echo "[3/3] Environment ready"
echo "=== post-start complete ==="
