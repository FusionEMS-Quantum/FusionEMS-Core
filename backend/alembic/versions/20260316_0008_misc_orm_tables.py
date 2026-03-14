"""Add misc ORM model tables: fatigue, deployment, fire RMS, platform core

Revision ID: 20260316_0008
Revises: 20260316_0007
Create Date: 2026-03-16 00:08:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0008"
down_revision = "20260316_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── fatigue_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "fatigue_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("risk_level", sa.String(32), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.String(1024), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_fatigue_logs_user_id", "fatigue_logs", ["user_id"])
    op.create_index("ix_fatigue_logs_risk_level", "fatigue_logs", ["risk_level"])

    # ── retry_schedules ───────────────────────────────────────────────────────
    op.create_table(
        "retry_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deployment_run_id", UUID(as_uuid=True),
                  sa.ForeignKey("deployment_runs.id"), nullable=False),
        sa.Column("step_name", sa.String(128), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_retry_schedules_deployment_run_id", "retry_schedules", ["deployment_run_id"])
    op.create_index("ix_retry_schedules_next_retry_at", "retry_schedules", ["next_retry_at"])

    # ── failure_audits ────────────────────────────────────────────────────────
    op.create_table(
        "failure_audits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deployment_run_id", UUID(as_uuid=True),
                  sa.ForeignKey("deployment_runs.id"), nullable=True),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("what_is_wrong", sa.String(1024), nullable=False),
        sa.Column("why_it_matters", sa.String(1024), nullable=False),
        sa.Column("what_to_do_next", sa.String(1024), nullable=False),
        sa.Column("business_context", sa.String(1024), nullable=True),
        sa.Column("human_review_status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_failure_audits_severity", "failure_audits", ["severity"])
    op.create_index("ix_failure_audits_resolved", "failure_audits", ["resolved"])

    # ── fire_inspection_violations ────────────────────────────────────────────
    op.create_table(
        "fire_inspection_violations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("inspection_id", UUID(as_uuid=True),
                  sa.ForeignKey("fire_inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_reference", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'OUTSTANDING'")),
        sa.Column("correction_due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("corrected_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_fire_inspection_violations_inspection_id",
                    "fire_inspection_violations", ["inspection_id"])

    # ── implementation_projects (platform_core.py) ────────────────────────────
    op.create_table(
        "implementation_projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("current_state", sa.String(64), nullable=False,
                  server_default=sa.text("'IMPLEMENTATION_CREATED'")),
        sa.Column("target_go_live_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_go_live_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_blob", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_implementation_projects_tenant_id", "implementation_projects", ["tenant_id"])
    op.create_index("ix_implementation_projects_current_state", "implementation_projects", ["current_state"])


def downgrade() -> None:
    op.drop_table("implementation_projects")
    op.drop_table("fire_inspection_violations")
    op.drop_table("failure_audits")
    op.drop_table("retry_schedules")
    op.drop_table("fatigue_logs")
