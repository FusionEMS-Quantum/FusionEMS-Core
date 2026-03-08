# ─────────────────────────────────────────────────────────────────────
# FusionEMS-Core — Developer Task Runner
# One-command access to every critical engineering operation.
# ─────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.DEFAULT_GOAL := help

VENV := .venv/bin
BACKEND := backend
FRONTEND := frontend
PYTHON := $(VENV)/python
PIP := $(VENV)/pip
PYTEST := $(VENV)/python -m pytest
ALEMBIC := cd $(BACKEND) && ../$(VENV)/python -m alembic

# ── Help ──────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show all available commands
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║           FusionEMS-Core  —  Developer Commands             ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Environment Setup ─────────────────────────────────────────────────

.PHONY: setup
setup: ## Full first-time setup (venv + deps + env files + migrations)
	@echo "▸ Creating virtual environment..."
	@test -d .venv || python3 -m venv .venv
	@$(PIP) install --upgrade pip --quiet
	@echo "▸ Installing backend dependencies..."
	@$(PIP) install -r $(BACKEND)/requirements.txt -r $(BACKEND)/requirements-dev.txt --quiet
	@$(PIP) install psycopg2-binary --quiet 2>/dev/null || true
	@echo "▸ Installing frontend dependencies..."
	@cd $(FRONTEND) && npm ci --prefer-offline 2>/dev/null || npm install
	@echo "▸ Copying env files..."
	@test -f $(BACKEND)/.env || cp $(BACKEND)/.env.example $(BACKEND)/.env
	@test -f $(FRONTEND)/.env || cp $(FRONTEND)/.env.example $(FRONTEND)/.env
	@echo "▸ Setup complete."

.PHONY: env
env: ## Copy .env.example files if .env does not exist
	@test -f $(BACKEND)/.env || cp $(BACKEND)/.env.example $(BACKEND)/.env && echo "  backend/.env created"
	@test -f $(FRONTEND)/.env || cp $(FRONTEND)/.env.example $(FRONTEND)/.env && echo "  frontend/.env created"

# ── Infrastructure ────────────────────────────────────────────────────

.PHONY: up
up: ## Start all Docker services (Postgres, Redis, OPA, OTEL, etc.)
	@bash scripts/codespace-up.sh

.PHONY: down
down: ## Stop all Docker services
	docker compose down

.PHONY: reset-db
reset-db: ## Drop and recreate the dev database (DESTRUCTIVE)
	@echo "⚠  This will destroy all local database data."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS fusionems;"
	docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE fusionems;"
	@$(MAKE) migrate
	@echo "▸ Database reset complete."

# ── Backend ───────────────────────────────────────────────────────────

.PHONY: backend
backend: ## Start the FastAPI backend (uvicorn, port 8000)
	cd $(BACKEND) && ../$(VENV)/python -m uvicorn core_app.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: backend-bg
backend-bg: ## Start the backend in background
	cd $(BACKEND) && nohup ../$(VENV)/python -m uvicorn core_app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/fusionems-backend.log 2>&1 &
	@echo "▸ Backend started (log: /tmp/fusionems-backend.log)"

# ── Frontend ──────────────────────────────────────────────────────────

.PHONY: frontend
frontend: ## Start the Next.js frontend (port 3000)
	cd $(FRONTEND) && npm run dev

.PHONY: frontend-build
frontend-build: ## Build the frontend for production
	cd $(FRONTEND) && rm -rf .next && npm run build

# ── Database Migrations ───────────────────────────────────────────────

.PHONY: migrate
migrate: ## Run all pending Alembic migrations
	$(ALEMBIC) upgrade head

.PHONY: migrate-status
migrate-status: ## Show current migration status
	$(ALEMBIC) current
	@echo "---"
	$(ALEMBIC) history --verbose -r-3:

.PHONY: migrate-new
migrate-new: ## Create a new migration (usage: make migrate-new MSG="add_xyz_table")
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

.PHONY: migrate-down
migrate-down: ## Rollback one migration
	$(ALEMBIC) downgrade -1

# ── Testing ───────────────────────────────────────────────────────────

.PHONY: test
test: ## Run all backend tests
	cd $(BACKEND) && ../$(PYTEST) tests/ -v --tb=short

.PHONY: test-fast
test-fast: ## Run backend tests (fail fast, no verbose)
	cd $(BACKEND) && ../$(PYTEST) tests/ -x --tb=line -q

.PHONY: test-smoke
test-smoke: ## Run smoke tests (requires live database)
	cd $(BACKEND) && ../$(PYTEST) tests/smoke/ -v --tb=short -m smoke

.PHONY: test-billing
test-billing: ## Run billing-specific tests
	cd $(BACKEND) && ../$(PYTEST) tests/ -v -k "billing"

.PHONY: test-crewlink
test-crewlink: ## Run CrewLink paging tests
	cd $(BACKEND) && ../$(PYTEST) tests/ -v -k "crewlink"

.PHONY: test-frontend
test-frontend: ## Run frontend component tests
	cd $(FRONTEND) && npm test

.PHONY: test-all
test-all: test test-frontend ## Run all backend + frontend tests

.PHONY: coverage
coverage: ## Run tests with coverage report
	cd $(BACKEND) && ../$(PYTEST) tests/ --cov=core_app --cov-report=term-missing --cov-report=html:htmlcov

# ── Code Quality ──────────────────────────────────────────────────────

.PHONY: lint
lint: ## Lint backend (ruff) + frontend (eslint)
	$(VENV)/ruff check $(BACKEND)/ --fix
	cd $(FRONTEND) && npm run lint

.PHONY: format
format: ## Format backend code (ruff)
	$(VENV)/ruff format $(BACKEND)/

.PHONY: typecheck
typecheck: ## Run frontend TypeScript type check
	cd $(FRONTEND) && ./node_modules/.bin/tsc --noEmit

.PHONY: precommit
precommit: ## Run all pre-commit hooks
	$(VENV)/pre-commit run --all-files

# ── Health & Diagnostics ──────────────────────────────────────────────

.PHONY: health
health: ## Run health check diagnostics
	bash scripts/codespace-health.sh

.PHONY: doctor
doctor: ## Run developer environment doctor (checks everything)
	bash scripts/dev-doctor.sh

.PHONY: seed
seed: ## Seed the development database with test data
	$(PYTHON) backend/scripts/seed_dev_db.py

# ── CI Simulation ─────────────────────────────────────────────────────

.PHONY: ci
ci: lint test typecheck frontend-build ## Simulate full CI pipeline locally
	@echo ""
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║                  ✓ All CI gates passed                      ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"

# ── Cleanup ───────────────────────────────────────────────────────────

.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -prune -o -name "*.pyc" -exec rm -f {} + 2>/dev/null || true
	rm -rf $(BACKEND)/htmlcov $(FRONTEND)/.next
