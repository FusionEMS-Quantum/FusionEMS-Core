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

echo "[3/6] Installing frontend dependencies..."
if [ -d frontend ] && [ -f frontend/package.json ]; then
  (cd frontend && npm ci --prefer-offline 2>/dev/null || npm install)
fi

echo "[4/6] Copying .env files (if missing)..."
if [ -f backend/.env.example ] && [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "  Created backend/.env from .env.example"
fi
if [ -f frontend/.env.example ] && [ ! -f frontend/.env.local ]; then
  cp frontend/.env.example frontend/.env.local
  echo "  Created frontend/.env.local from .env.example"
fi

echo "[5/6] Installing pre-commit hooks..."
if command -v pre-commit &>/dev/null; then
  pre-commit install --install-hooks 2>/dev/null || echo "  Pre-commit hooks installed (some hook repos may be slow)"
else
  pip install pre-commit --quiet
  pre-commit install --install-hooks 2>/dev/null || true
fi

echo "[6/6] Verifying tool availability..."
python3 --version
node --version 2>/dev/null || echo "  Node.js: not available"
docker --version 2>/dev/null || echo "  Docker: not available"

echo "=== post-create complete ==="
