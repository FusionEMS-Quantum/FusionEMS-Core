#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pass() { echo "[PASS] $1"; }

# 1) Frontend deterministic build
(
  cd frontend
  npm run ci
)
pass "frontend ci/build"

# 2) Backend import/runtime readiness
if [[ ! -f .venv/bin/activate ]]; then
  python3 -m venv .venv
  . .venv/bin/activate
  pip install -r backend/requirements.txt -r backend/requirements-dev.txt
else
  . .venv/bin/activate
fi
(
  cd backend
  DATABASE_URL='postgresql://user:pass@localhost:5432/db' \
  JWT_SECRET_KEY='release_validation_jwt_secret_key_1234567890' \
  python - <<'PY'
import core_app.main
print('backend import smoke: ok')
PY
)
pass "backend import smoke"

# 3) Backend pytest
(
  cd backend
  DATABASE_URL='postgresql://user:pass@localhost:5432/db' \
  JWT_SECRET_KEY='release_validation_jwt_secret_key_1234567890' \
  python -m pytest -q
)
pass "backend pytest"

# 4) Canonical go-live static gate
python scripts/centralized_go_live_gate.py
pass "centralized go-live gate"

# 5) Real runtime validation (auth live-status + Telnyx readiness)
python scripts/release_runtime_validation.py
pass "runtime live-status/telnyx validation"

echo "ALL GATES GREEN"
