#!/usr/bin/env bash
# FusionEMS-Core — Deterministic Codespace Setup
# This script runs ONCE when the container is created.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== FusionEMS-Core: post-create ==="

# Python virtual environment (deterministic)
if [ ! -d .venv ]; then
  echo "[1/4] Creating Python virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "[2/4] Installing backend dependencies..."
pip install --upgrade pip --quiet
pip install -r backend/requirements.txt -r backend/requirements-dev.txt --quiet
# psycopg2-binary for local dev (avoids libpq-dev requirement)
pip install psycopg2-binary --quiet 2>/dev/null || true

echo "[3/4] Installing frontend dependencies..."
if [ -d frontend ] && [ -f frontend/package.json ]; then
  (cd frontend && npm ci --prefer-offline 2>/dev/null || npm install)
fi

echo "[4/4] Verifying tool availability..."
python3 --version
node --version 2>/dev/null || echo "  Node.js: not available"
docker --version 2>/dev/null || echo "  Docker: not available"

echo "=== post-create complete ==="
