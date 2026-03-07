# FusionEMS Quantum — Core Platform

**Enterprise-grade EMS operations platform** built on FastAPI, Next.js, and Terraform-managed AWS infrastructure.

## Architecture

| Layer              | Stack                                                  |
|--------------------|--------------------------------------------------------|
| **Frontend**       | Next.js 14 · React 18 · Tailwind CSS · Radix UI        |
| **Backend**        | FastAPI · SQLAlchemy 2 · PostgreSQL (PostGIS) · Redis  |
| **Infrastructure** | Terraform (multi-env) · ECS Fargate · CloudFront · WAF |
| **Observability**  | OpenTelemetry · Prometheus · Grafana                   |
| **Security**       | OIDC · OPA policies · Checkov · Cognito                |

## Quick Start (Local Development)

```bash
docker compose up -d
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Grafana**: http://localhost:3001

## Project Structure

```
backend/       FastAPI application and core business logic
frontend/      Next.js frontend application
infra/         Terraform modules and environment configs
  terraform/
    modules/   Reusable infrastructure modules
    environments/  dev · staging · prod · dr
opa/           Open Policy Agent policies
otel/          OpenTelemetry collector config
prometheus/    Prometheus scrape configuration
grafana/       Grafana dashboard provisioning
schemas/       Data schemas and validation
scripts/       Utility and deployment scripts
```

## Deployment

See [`README_DEPLOY.md`](README_DEPLOY.md) for the full deployment runbook.


## Codespaces / local runtime

This repo runs as a multiple-service application. The frontend is in `frontend/`, the backend is in `backend/`, and local development is expected to use `docker-compose.yml`.

Recommended local / Codespaces flow:

```bash
bash scripts/codespace-up.sh
bash scripts/codespace-health.sh
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

Backend:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn core_app.main:app --host 0.0.0.0 --port 8000 --reload
```

Environment samples are provided in `frontend/.env.example` and `backend/.env.example`.
