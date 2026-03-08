# pylint: skip-file
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

"""AI Platform — use-case registry, workflow orchestration, governance, override, copilots

Revision ID: 20260307_0030
Revises: e294733db472
Create Date: 2026-03-07

Creates all AI platform tables for:
  - Use-case registry (ai_use_cases, ai_use_case_versions, ai_model_bindings, ai_prompt_templates, ai_use_case_audit_events)
  - Workflow orchestration (ai_workflow_runs, ai_context_snapshots, ai_workflow_failures, ai_fallback_decisions)
  - Safety + governance (ai_guardrail_rules, ai_approval_requirements, ai_protected_actions, ai_governance_decisions, ai_restricted_output_events)
  - Explainability (ai_explanation_records, ai_confidence_records, ai_output_tags)
  - Human override (ai_human_override_events, ai_review_items, ai_approval_events, ai_rejection_events, ai_resume_events)
  - Domain copilots (ai_domain_copilots, ai_domain_policies, ai_copilot_action_boundaries, ai_copilot_audit_events)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260307_0030"
down_revision: Union[str, None] = "e294733db472"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── AI USE-CASE REGISTRY ──────────────────────────────────────────────

    op.create_table(
        "ai_use_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("purpose", sa.Text, nullable=False),
        sa.Column("model_provider", sa.String(100), nullable=False),
        sa.Column("prompt_template_id", sa.String(100), nullable=False),
        sa.Column("risk_tier", sa.String(20), nullable=False, server_default="MODERATE_RISK"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("fallback_behavior", sa.String(255), nullable=False),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("allowed_data_scope", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("human_override_behavior", sa.String(50), nullable=False, server_default="pause_and_review"),
        sa.Column("last_review_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_use_case_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("use_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_use_cases.id"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("changed_by", sa.String(255), nullable=False),
        sa.Column("change_reason", sa.Text, nullable=False),
        sa.Column("snapshot", postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_model_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("use_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_use_cases.id"), nullable=False, unique=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="4096"),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="30"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("template_key", sa.String(100), nullable=False, index=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("user_prompt_template", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_use_case_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("use_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_use_cases.id"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("detail", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── AI WORKFLOW ORCHESTRATION ─────────────────────────────────────────

    op.create_table(
        "ai_workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("use_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_use_cases.id"), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(255), nullable=False, index=True),
        sa.Column("state", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("governance_state", sa.String(30), nullable=False, server_default="ALLOWED"),
        sa.Column("override_state", sa.String(30), nullable=False, server_default="AI_ACTIVE"),
        sa.Column("context_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("provider_response", postgresql.JSONB, nullable=True),
        sa.Column("fallback_used", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("confidence_level", sa.String(10), nullable=True),
        sa.Column("explanation_summary", sa.Text, nullable=True),
        sa.Column("next_step", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_context_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("context_type", sa.String(50), nullable=False),
        sa.Column("context_data", postgresql.JSONB, nullable=False),
        sa.Column("data_scope_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_workflow_failures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("failure_type", sa.String(50), nullable=False),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text, nullable=False),
        sa.Column("provider_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_fallback_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("fallback_type", sa.String(50), nullable=False),
        sa.Column("original_error", sa.Text, nullable=False),
        sa.Column("fallback_output", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── AI SAFETY + GOVERNANCE ────────────────────────────────────────────

    op.create_table(
        "ai_guardrail_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("enforcement", sa.String(20), nullable=False, server_default="BLOCK"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("conditions", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_approval_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("use_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_use_cases.id"), nullable=True, index=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("action_name", sa.String(255), nullable=False),
        sa.Column("required_role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_protected_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("action_name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("risk_tier", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("requires_human", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_governance_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_guardrail_rules.id"), nullable=True),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_restricted_output_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("output_class", sa.String(100), nullable=False),
        sa.Column("redacted_fields", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── AI EXPLAINABILITY + CONFIDENCE ────────────────────────────────────

    op.create_table(
        "ai_explanation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("what_is_wrong", sa.Text, nullable=False),
        sa.Column("why_it_matters", sa.Text, nullable=False),
        sa.Column("what_you_should_do", sa.Text, nullable=False),
        sa.Column("domain_context", sa.Text, nullable=False),
        sa.Column("human_review", sa.String(30), nullable=False),
        sa.Column("confidence", sa.String(10), nullable=False),
        sa.Column("simple_mode_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_confidence_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("confidence_level", sa.String(10), nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_output_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("tag_key", sa.String(100), nullable=False),
        sa.Column("tag_value", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── HUMAN OVERRIDE + REVIEW ───────────────────────────────────────────

    op.create_table(
        "ai_human_override_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_state", sa.String(30), nullable=False),
        sa.Column("new_state", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_review_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("review_type", sa.String(50), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="REVIEW_PENDING"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_approval_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("review_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_review_items.id"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_rejection_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("review_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_review_items.id"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("regenerate_requested", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_resume_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_workflow_runs.id"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── DOMAIN COPILOTS ───────────────────────────────────────────────────

    op.create_table(
        "ai_domain_copilots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("base_prompt_template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_prompt_templates.id"), nullable=True),
        sa.Column("explanation_rules", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("data_scope_controls", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_domain_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("copilot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_domain_copilots.id"), nullable=False, index=True),
        sa.Column("policy_name", sa.String(255), nullable=False),
        sa.Column("policy_description", sa.Text, nullable=False),
        sa.Column("enforcement_level", sa.String(20), nullable=False, server_default="BLOCK"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_copilot_action_boundaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("copilot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_domain_copilots.id"), nullable=False, index=True),
        sa.Column("action_name", sa.String(255), nullable=False),
        sa.Column("is_allowed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("requires_human_review", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "ai_copilot_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("copilot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_domain_copilots.id"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_attempted", sa.String(255), nullable=False),
        sa.Column("was_blocked", sa.Boolean, nullable=False),
        sa.Column("block_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── ROW-LEVEL SECURITY ────────────────────────────────────────────────
    # Enable RLS on all AI platform tables for tenant isolation

    _ai_tables = [
        "ai_use_cases", "ai_use_case_versions", "ai_model_bindings",
        "ai_prompt_templates", "ai_use_case_audit_events",
        "ai_workflow_runs", "ai_context_snapshots",
        "ai_workflow_failures", "ai_fallback_decisions",
        "ai_guardrail_rules", "ai_approval_requirements",
        "ai_protected_actions", "ai_governance_decisions",
        "ai_restricted_output_events",
        "ai_explanation_records", "ai_confidence_records", "ai_output_tags",
        "ai_human_override_events", "ai_review_items",
        "ai_approval_events", "ai_rejection_events", "ai_resume_events",
        "ai_domain_copilots", "ai_domain_policies",
        "ai_copilot_action_boundaries", "ai_copilot_audit_events",
    ]

    for tbl in _ai_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{tbl} ON {tbl} "
            f"USING (tenant_id = current_setting('app.tenant_id')::uuid)"
        )


def downgrade() -> None:
    _ai_tables = [
        "ai_copilot_audit_events", "ai_copilot_action_boundaries",
        "ai_domain_policies", "ai_domain_copilots",
        "ai_resume_events", "ai_rejection_events",
        "ai_approval_events", "ai_review_items",
        "ai_human_override_events",
        "ai_output_tags", "ai_confidence_records", "ai_explanation_records",
        "ai_restricted_output_events", "ai_governance_decisions",
        "ai_protected_actions", "ai_approval_requirements", "ai_guardrail_rules",
        "ai_fallback_decisions", "ai_workflow_failures",
        "ai_context_snapshots", "ai_workflow_runs",
        "ai_use_case_audit_events", "ai_prompt_templates",
        "ai_model_bindings", "ai_use_case_versions", "ai_use_cases",
    ]
    for tbl in _ai_tables:
        op.drop_table(tbl)
