"""AI Platform gap tables — queue items, user-facing summaries, tenant settings.

Revision ID: ai_gap_tables_001
Revises: 20260307_0030_ai_platform_tables
Create Date: 2026-03-07 12:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ai_gap_tables_001"
down_revision = None  # standalone — depends on 20260307_0030_ai_platform_tables existing
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── AI Queue Items ────────────────────────────────────────────────────
    op.create_table(
        "ai_queue_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_workflow_runs.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "use_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_use_cases.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "queue_name",
            sa.String(50),
            nullable=False,
            server_default="default",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("picked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── AI User-Facing Summaries ──────────────────────────────────────────
    op.create_table(
        "ai_user_facing_summaries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_workflow_runs.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("what_happened", sa.Text, nullable=False),
        sa.Column("why_it_matters", sa.Text, nullable=False),
        sa.Column("do_this_next", sa.Text, nullable=False),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column(
            "is_simple_mode",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── AI Tenant Settings ────────────────────────────────────────────────
    op.create_table(
        "ai_tenant_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "ai_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "default_risk_tier",
            sa.String(20),
            nullable=False,
            server_default="MODERATE_RISK",
        ),
        sa.Column(
            "auto_approve_low_risk",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "require_human_review_high_risk",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "max_concurrent_workflows",
            sa.Integer,
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "global_confidence_threshold",
            sa.String(10),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column(
            "allowed_domains",
            postgresql.JSONB,
            nullable=False,
            server_default='{"billing": true, "clinical": true, "dispatch": true, "readiness": true, "support": true, "founder": true}',
        ),
        sa.Column(
            "environment_ai_toggle",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ── Row-Level Security ────────────────────────────────────────────────
    _new_tables = [
        "ai_queue_items",
        "ai_user_facing_summaries",
        "ai_tenant_settings",
    ]
    for tbl in _new_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{tbl} ON {tbl} "
            f"USING (tenant_id = current_setting('app.tenant_id')::uuid)"
        )


def downgrade() -> None:
    for tbl in ["ai_tenant_settings", "ai_user_facing_summaries", "ai_queue_items"]:
        op.drop_table(tbl)
