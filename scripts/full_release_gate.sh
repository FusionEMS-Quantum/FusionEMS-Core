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
. .venv/bin/activate
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

# 5) Authenticated live-status + telnyx runtime validation (must be healthy)
TMP_JSON="$(mktemp)"
set +e
PYTHONPATH=backend python scripts/release_runtime_validation.py > "$TMP_JSON"
STATUS=$?
set -e
cat "$TMP_JSON"
python - "$TMP_JSON" "$STATUS" <<'PY'
import json
import sys

path = sys.argv[1]
status = int(sys.argv[2])
raw = open(path).read()
marker = '{\n  "live_status_http"'
start = raw.find(marker)
if start == -1:
    raise SystemExit('runtime validation JSON payload missing')
obj = json.loads(raw[start:])
if status != 0:
    raise SystemExit('runtime validation command failed')
if obj.get('live_status_http') != 200:
    raise SystemExit('live-status auth check not healthy')
if not obj.get('telnyx_runtime_validation', {}).get('healthy'):
    raise SystemExit('telnyx runtime readiness is not healthy')
PY
pass "runtime live-status/telnyx validation"

echo "ALL GATES GREEN"
