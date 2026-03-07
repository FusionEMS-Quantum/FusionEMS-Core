"""create deployment_runs and deployment_steps tables

Revision ID: 20260307_0027
Revises: 20260307_0026
Create Date: 2026-03-07

Tables: deployment_runs, deployment_steps, webhook_event_logs (provisioning audit)

These tables support the zero-error deployment state machine for agency onboarding.
Every agency signup flows through a DeploymentRun with step-by-step audit entries.
"""
from __future__ import annotations

from alembic import op

revision = "20260307_0027"
down_revision = "20260307_0026"
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        __import__("sqlalchemy").text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t)"
        ),
        {"t": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    # ── deployment_runs ───────────────────────────────────────────────────────
    if not _table_exists(conn, "deployment_runs"):
        op.execute("""
            CREATE TABLE deployment_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                external_event_id TEXT NOT NULL UNIQUE,
                agency_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
                current_state TEXT NOT NULL DEFAULT 'CHECKOUT_CREATED',
                failure_reason TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                metadata_blob JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_deployment_runs_external_event_id "
            "ON deployment_runs (external_event_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_deployment_runs_current_state "
            "ON deployment_runs (current_state)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_deployment_runs_agency_id "
            "ON deployment_runs (agency_id)"
        )

    # ── deployment_steps ──────────────────────────────────────────────────────
    if not _table_exists(conn, "deployment_steps"):
        op.execute("""
            CREATE TABLE deployment_steps (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL REFERENCES deployment_runs(id) ON DELETE CASCADE,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL,
                result_blob JSONB NOT NULL DEFAULT '{}',
                error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_deployment_steps_run_id "
            "ON deployment_steps (run_id)"
        )

    # ── webhook_event_logs ────────────────────────────────────────────────────
    # Persistent log of every incoming webhook (Stripe, LOB, Telnyx) for replay.
    if not _table_exists(conn, "webhook_event_logs"):
        op.execute("""
            CREATE TABLE webhook_event_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source TEXT NOT NULL,
                event_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload JSONB NOT NULL DEFAULT '{}',
                processed BOOLEAN NOT NULL DEFAULT FALSE,
                correlation_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_webhook_event_logs_source_event_id "
            "ON webhook_event_logs (source, event_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_webhook_event_logs_event_type "
            "ON webhook_event_logs (event_type)"
        )

    # ── provisioning_attempts ─────────────────────────────────────────────────
    # Tracks individual retry attempts for a deployment run.
    if not _table_exists(conn, "provisioning_attempts"):
        op.execute("""
            CREATE TABLE provisioning_attempts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                run_id UUID NOT NULL REFERENCES deployment_runs(id) ON DELETE CASCADE,
                attempt_number INTEGER NOT NULL DEFAULT 1,
                outcome TEXT NOT NULL DEFAULT 'PENDING',
                error_detail TEXT,
                started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                completed_at TIMESTAMPTZ
            )
        """)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_provisioning_attempts_run_id "
            "ON provisioning_attempts (run_id)"
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS provisioning_attempts CASCADE")
    op.execute("DROP TABLE IF EXISTS webhook_event_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS deployment_steps CASCADE")
    op.execute("DROP TABLE IF EXISTS deployment_runs CASCADE")
