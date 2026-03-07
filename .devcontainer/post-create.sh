#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -d frontend ]; then
  (cd frontend && npm ci)
fi
if [ -d backend ]; then
  python3 -m pip install --upgrade pip
  python3 -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt psycopg2-binary
fi
