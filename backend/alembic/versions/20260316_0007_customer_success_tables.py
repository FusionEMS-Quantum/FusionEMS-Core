"""Add customer success tables

Revision ID: 20260316_0007
Revises: 20260316_0006
Create Date: 2026-03-16 00:07:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0007"
down_revision = "20260316_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Training (must come first due to FK chain) ───────────────────────────

    op.create_table(
        "cs_training_tracks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("track_type", sa.String(64), nullable=True),
        sa.Column("curriculum", JSONB(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_training_tracks_tenant_id", "cs_training_tracks", ["tenant_id"])

    op.create_table(
        "cs_training_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("track_id", UUID(as_uuid=True), sa.ForeignKey("cs_training_tracks.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(64), nullable=True),
        sa.Column("assigned_by", UUID(as_uuid=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'ASSIGNED'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_training_assignments_tenant_id", "cs_training_assignments", ["tenant_id"])
    op.create_index("ix_cs_training_assignments_track_id", "cs_training_assignments", ["track_id"])

    op.create_table(
        "cs_training_completions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("assignment_id", UUID(as_uuid=True), sa.ForeignKey("cs_training_assignments.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("module_name", sa.String(255), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_training_completions_assignment_id", "cs_training_completions", ["assignment_id"])

    op.create_table(
        "cs_training_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("completion_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_training_completions.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("verified_by", UUID(as_uuid=True), nullable=True),
        sa.Column("method", sa.String(32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_training_verifications_completion_id", "cs_training_verifications", ["completion_id"])

    # ─── Implementation ───────────────────────────────────────────────────────

    op.create_table(
        "cs_implementation_projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PLANNING'")),
        sa.Column("target_go_live_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_go_live_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_implementation_projects_tenant_id", "cs_implementation_projects", ["tenant_id"])

    op.create_table(
        "cs_implementation_milestones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_implementation_projects.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phase", sa.String(64), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_implementation_milestones_project_id", "cs_implementation_milestones", ["project_id"])

    op.create_table(
        "cs_implementation_training_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_implementation_projects.id"), nullable=False),
        sa.Column("assignment_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_training_assignments.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_impl_training_links_project_id", "cs_implementation_training_links", ["project_id"])

    op.create_table(
        "cs_implementation_risk_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_implementation_projects.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("flag_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default=sa.text("'MEDIUM'")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_impl_risk_flags_project_id", "cs_implementation_risk_flags", ["project_id"])

    op.create_table(
        "cs_stabilization_checkpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_implementation_projects.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("checkpoint_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("confirmed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_stabilization_checkpoints_project_id", "cs_stabilization_checkpoints", ["project_id"])

    op.create_table(
        "cs_success_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("diff", JSONB(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_success_audit_events_tenant_id", "cs_success_audit_events", ["tenant_id"])

    # ─── Support ──────────────────────────────────────────────────────────────

    op.create_table(
        "cs_support_tickets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("subject", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("priority", sa.String(32), nullable=False, server_default=sa.text("'NORMAL'")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("submitted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to", UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_support_tickets_tenant_id", "cs_support_tickets", ["tenant_id"])
    op.create_index("ix_cs_support_tickets_status", "cs_support_tickets", ["status"])

    op.create_table(
        "cs_support_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("cs_support_tickets.id"), nullable=False),
        sa.Column("author_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_support_notes_ticket_id", "cs_support_notes", ["ticket_id"])

    op.create_table(
        "cs_support_escalations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("cs_support_tickets.id"), nullable=False),
        sa.Column("escalated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("escalation_level", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_support_escalations_ticket_id", "cs_support_escalations", ["ticket_id"])

    op.create_table(
        "cs_support_sla_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("cs_support_tickets.id"), nullable=False),
        sa.Column("sla_type", sa.String(32), nullable=False),
        sa.Column("target_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_support_sla_events_ticket_id", "cs_support_sla_events", ["ticket_id"])

    op.create_table(
        "cs_support_resolution_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("cs_support_tickets.id"), nullable=False),
        sa.Column("resolved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_type", sa.String(64), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("customer_satisfaction_score", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_support_resolution_events_ticket_id", "cs_support_resolution_events", ["ticket_id"])

    op.create_table(
        "cs_support_state_transitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("cs_support_tickets.id"), nullable=False),
        sa.Column("from_state", sa.String(32), nullable=True),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("transitioned_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("transitioned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_support_state_transitions_ticket_id", "cs_support_state_transitions", ["ticket_id"])

    # ─── Enablement Audit ─────────────────────────────────────────────────────

    op.create_table(
        "cs_enablement_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=True),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("diff", JSONB(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_enablement_audit_events_tenant_id", "cs_enablement_audit_events", ["tenant_id"])

    # ─── Account Health ───────────────────────────────────────────────────────

    op.create_table(
        "cs_account_health_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("composite_score", sa.Float(), nullable=True),
        sa.Column("trend", sa.String(16), nullable=True),
        sa.Column("components", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("computed_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_account_health_snapshots_tenant_id", "cs_account_health_snapshots", ["tenant_id"])
    op.create_index("ix_cs_account_health_snapshots_snapshot_at", "cs_account_health_snapshots", ["snapshot_at"])

    op.create_table(
        "cs_success_risk_factors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_account_health_snapshots.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("factor_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("mitigated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mitigated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_success_risk_factors_snapshot_id", "cs_success_risk_factors", ["snapshot_id"])

    op.create_table(
        "cs_health_computation_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("snapshot_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_account_health_snapshots.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("computation_method", sa.String(64), nullable=True),
        sa.Column("inputs", JSONB(), nullable=True),
        sa.Column("output", JSONB(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_health_computation_logs_snapshot_id", "cs_health_computation_logs", ["snapshot_id"])

    # ─── Adoption, Expansion, Renewal ────────────────────────────────────────

    op.create_table(
        "cs_adoption_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("metric_type", sa.String(64), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_adoption_metrics_tenant_id", "cs_adoption_metrics", ["tenant_id"])

    op.create_table(
        "cs_workflow_adoption_metrics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("workflow", sa.String(64), nullable=False),
        sa.Column("events_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("active_users", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_workflow_adoption_metrics_tenant_id", "cs_workflow_adoption_metrics", ["tenant_id"])

    op.create_table(
        "cs_expansion_readiness_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("signal_type", sa.String(64), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_expansion_readiness_signals_tenant_id", "cs_expansion_readiness_signals", ["tenant_id"])

    op.create_table(
        "cs_renewal_risk_signals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("signal_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_renewal_risk_signals_tenant_id", "cs_renewal_risk_signals", ["tenant_id"])

    op.create_table(
        "cs_expansion_opportunities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("opportunity_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'IDENTIFIED'")),
        sa.Column("estimated_arr_delta", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("identified_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_expansion_opportunities_tenant_id", "cs_expansion_opportunities", ["tenant_id"])

    op.create_table(
        "cs_stakeholder_engagement_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("cs_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("stakeholder_name", sa.String(255), nullable=True),
        sa.Column("stakeholder_role", sa.String(64), nullable=True),
        sa.Column("engagement_type", sa.String(64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(255), nullable=True),
        sa.Column("engaged_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_stakeholder_engagement_notes_tenant_id", "cs_stakeholder_engagement_notes", ["tenant_id"])

    # ─── Value Milestones ─────────────────────────────────────────────────────

    op.create_table(
        "cs_value_milestones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("achieved_value", sa.Float(), nullable=True),
        sa.Column("achieved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("achieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_value_milestones_tenant_id", "cs_value_milestones", ["tenant_id"])

    op.create_table(
        "cs_milestone_update_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("milestone_id", UUID(as_uuid=True),
                  sa.ForeignKey("cs_implementation_milestones.id"), nullable=False),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at_event", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cs_milestone_update_logs_milestone_id", "cs_milestone_update_logs", ["milestone_id"])


def downgrade() -> None:
    op.drop_table("cs_milestone_update_logs")
    op.drop_table("cs_value_milestones")
    op.drop_table("cs_stakeholder_engagement_notes")
    op.drop_table("cs_expansion_opportunities")
    op.drop_table("cs_renewal_risk_signals")
    op.drop_table("cs_expansion_readiness_signals")
    op.drop_table("cs_workflow_adoption_metrics")
    op.drop_table("cs_adoption_metrics")
    op.drop_table("cs_health_computation_logs")
    op.drop_table("cs_success_risk_factors")
    op.drop_table("cs_account_health_snapshots")
    op.drop_table("cs_enablement_audit_events")
    op.drop_table("cs_support_state_transitions")
    op.drop_table("cs_support_resolution_events")
    op.drop_table("cs_support_sla_events")
    op.drop_table("cs_support_escalations")
    op.drop_table("cs_support_notes")
    op.drop_table("cs_support_tickets")
    op.drop_table("cs_success_audit_events")
    op.drop_table("cs_stabilization_checkpoints")
    op.drop_table("cs_implementation_risk_flags")
    op.drop_table("cs_implementation_training_links")
    op.drop_table("cs_implementation_milestones")
    op.drop_table("cs_implementation_projects")
    op.drop_table("cs_training_verifications")
    op.drop_table("cs_training_completions")
    op.drop_table("cs_training_assignments")
    op.drop_table("cs_training_tracks")
