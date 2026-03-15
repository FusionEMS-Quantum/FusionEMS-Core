#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# FusionEMS-Core — Developer Environment Doctor
# Validates every requirement for a working development environment.
# Exit code 0 = all checks passed, 1 = critical failure detected.
# ─────────────────────────────────────────────────────────────────────
set -uo pipefail

PASS=0
WARN=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  ✓ PASS  $1"; }
warn() { WARN=$((WARN + 1)); echo "  ⚠ WARN  $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  ✗ FAIL  $1"; }

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         FusionEMS-Core  —  Dev Environment Doctor            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. Python ─────────────────────────────────────────────────────────
echo "─── Python ───"
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
        pass "Python $PY_VER"
    else
        warn "Python $PY_VER (3.11+ recommended)"
    fi
else
    fail "Python 3 not found"
fi

# ── 2. Virtual Environment ────────────────────────────────────────────
echo "─── Virtual Environment ───"
if [ -d ".venv" ]; then
    pass ".venv directory exists"
    if [ -f ".venv/bin/python" ]; then
        pass ".venv/bin/python executable"
    else
        fail ".venv/bin/python missing"
    fi
else
    fail ".venv not found (run: make setup)"
fi

if [ -n "${VIRTUAL_ENV:-}" ]; then
    pass "venv activated ($VIRTUAL_ENV)"
else
    warn "venv not activated (run: source .venv/bin/activate)"
fi

# ── 3. Node.js ────────────────────────────────────────────────────────
echo "─── Node.js ───"
if command -v node &>/dev/null; then
    NODE_VER=$(node --version | tr -d 'v')
    NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        pass "Node.js $NODE_VER"
    else
        warn "Node.js $NODE_VER (18+ recommended)"
    fi
else
    fail "Node.js not found"
fi

if command -v npm &>/dev/null; then
    pass "npm $(npm --version)"
else
    fail "npm not found"
fi

# ── 4. Docker ─────────────────────────────────────────────────────────
echo "─── Docker ───"
if command -v docker &>/dev/null; then
    if docker info &>/dev/null; then
        pass "Docker daemon running"
    else
        warn "Docker installed but daemon not running"
    fi
else
    warn "Docker not installed (optional for Codespaces)"
fi

if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    pass "docker compose available"
else
    warn "docker compose not available"
fi

# ── 4b. VS Code sandbox prerequisites ─────────────────────────────────
echo "─── VS Code Sandbox Prerequisites ───"
if command -v rg &>/dev/null; then
    pass "ripgrep available"
else
    fail "ripgrep missing (required by Copilot terminal sandbox)"
fi

if command -v bwrap &>/dev/null; then
    pass "bubblewrap available"
else
    fail "bubblewrap missing (required by Copilot terminal sandbox)"
fi

if command -v socat &>/dev/null; then
    pass "socat available"
else
    fail "socat missing (required by Copilot terminal sandbox)"
fi

# ── 5. Backend Dependencies ───────────────────────────────────────────
echo "─── Backend Dependencies ───"
if [ -f ".venv/bin/python" ]; then
    if .venv/bin/python -c "import fastapi" 2>/dev/null; then
        pass "FastAPI importable"
    else
        fail "FastAPI not installed (run: make setup)"
    fi
    if PYTHONPATH="$(pwd)/backend" .venv/bin/python -c "import core_app.main" 2>/dev/null; then
        pass "core_app importable from repo root with backend PYTHONPATH"
    else
        warn "core_app not importable from repo root unless backend PYTHONPATH is set"
    fi
    if (cd backend && ../.venv/bin/python -c "import core_app.main" 2>/dev/null); then
        pass "core_app importable from backend working directory"
    else
        fail "core_app not importable from backend working directory"
    fi
    if .venv/bin/python -c "import sqlalchemy" 2>/dev/null; then
        pass "SQLAlchemy importable"
    else
        fail "SQLAlchemy not installed"
    fi
    if .venv/bin/python -c "import alembic" 2>/dev/null; then
        pass "Alembic importable"
    else
        fail "Alembic not installed"
    fi
    if .venv/bin/python -c "import pytest" 2>/dev/null; then
        pass "pytest importable"
    else
        fail "pytest not installed (run: pip install -r backend/requirements-dev.txt)"
    fi
    if .venv/bin/python -c "import ruff" 2>/dev/null; then
        pass "ruff importable"
    else
        warn "ruff not installed"
    fi
else
    fail "Cannot check backend deps (venv missing)"
fi

# ── 6. Frontend Dependencies ──────────────────────────────────────────
echo "─── Frontend Dependencies ───"
if [ -d "frontend/node_modules" ]; then
    pass "frontend/node_modules present"
else
    fail "frontend/node_modules missing (run: cd frontend && npm ci)"
fi

if [ -f "frontend/node_modules/.bin/next" ]; then
    pass "Next.js installed"
else
    fail "Next.js binary not found"
fi

# ── 7. Environment Files ──────────────────────────────────────────────
echo "─── Environment Files ───"
if [ -f "backend/.env" ]; then
    pass "backend/.env exists"
elif [ -f "backend/.env.example" ]; then
    warn "backend/.env missing (run: make env)"
else
    fail "backend/.env AND .env.example both missing"
fi

if [ -f "frontend/.env" ] || [ -f "frontend/.env.local" ]; then
    pass "frontend/.env exists"
elif [ -f "frontend/.env.example" ]; then
    warn "frontend/.env missing (run: make env)"
else
    fail "frontend/.env AND .env.example both missing"
fi

# ── 8. Infrastructure Services ────────────────────────────────────────
echo "─── Infrastructure Services ───"
if command -v docker &>/dev/null && docker info &>/dev/null; then
    if docker compose ps --status running 2>/dev/null | grep -q postgres; then
        pass "PostgreSQL container running"
    else
        warn "PostgreSQL container not running (run: make up)"
    fi
    if docker compose ps --status running 2>/dev/null | grep -q redis; then
        pass "Redis container running"
    else
        warn "Redis container not running (run: make up)"
    fi
else
    warn "Docker not available — skipping container checks"
fi

# Check PostgreSQL connectivity
if command -v pg_isready &>/dev/null; then
    if pg_isready -h localhost -p 5432 -q 2>/dev/null; then
        pass "PostgreSQL accepting connections (port 5432)"
    else
        warn "PostgreSQL not accepting connections on port 5432"
    fi
fi

# ── 9. Port Availability ─────────────────────────────────────────────
echo "─── Port Availability ───"
for PORT in 3000 8000 5432 6379; do
    if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
        pass "Port $PORT in use (expected service)"
    else
        warn "Port $PORT not in use"
    fi
done

# ── 10. Git & Pre-commit ──────────────────────────────────────────────
echo "─── Git & Tools ───"
if command -v git &>/dev/null; then
    pass "git $(git --version | awk '{print $3}')"
else
    fail "git not found"
fi

if [ -f ".pre-commit-config.yaml" ]; then
    if command -v pre-commit &>/dev/null || [ -f ".venv/bin/pre-commit" ]; then
        pass "pre-commit available"
    else
        warn "pre-commit config exists but pre-commit not installed"
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────
echo ""
echo "─── Summary ───"
echo "  PASS: $PASS"
echo "  WARN: $WARN"
echo "  FAIL: $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "  ✗ Environment has $FAIL critical issue(s). Run: make setup"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo "  ⚠ Environment is functional with $WARN warning(s)."
    exit 0
else
    echo "  ✓ Environment is fully healthy."
    exit 0
fi
