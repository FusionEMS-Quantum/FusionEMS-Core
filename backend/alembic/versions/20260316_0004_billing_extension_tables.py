"""Add billing extension tables (claim issues, ledger, audit, approval events)

Revision ID: 20260316_0004
Revises: 20260316_0003
Create Date: 2026-03-16 00:04:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0004"
down_revision = "20260316_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # claim_issues
    op.create_table(
        "claim_issues",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default=sa.text("'MEDIUM'")),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("what_is_wrong", sa.String(1024), nullable=False),
        sa.Column("why_it_matters", sa.String(1024), nullable=False),
        sa.Column("what_to_do_next", sa.String(1024), nullable=False),
        sa.Column("business_context", sa.String(1024), nullable=True),
        sa.Column("human_review_status", sa.String(16), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_claim_issues_claim_id", "claim_issues", ["claim_id"])

    # patient_balance_ledger
    op.create_table(
        "patient_balance_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("balance_after_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_patient_balance_ledger_claim_id", "patient_balance_ledger", ["claim_id"])
    op.create_index("ix_patient_balance_ledger_patient_id", "patient_balance_ledger", ["patient_id"])

    # payment_link_events
    op.create_table(
        "payment_link_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("stripe_payment_link_id", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'CREATED'")),
        sa.Column("sent_via", sa.String(16), nullable=False, server_default=sa.text("'SMS'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_payment_link_events_claim_id", "payment_link_events", ["claim_id"])

    # collections_reviews
    op.create_table(
        "collections_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("reviewed_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason_for_hold", sa.String(255), nullable=True),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_collections_reviews_claim_id", "collections_reviews", ["claim_id"])

    # claim_audit_events
    op.create_table(
        "claim_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("old_value", sa.String(255), nullable=True),
        sa.Column("new_value", sa.String(255), nullable=True),
        sa.Column("metadata_blob", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_claim_audit_events_claim_id", "claim_audit_events", ["claim_id"])

    # reminder_events
    op.create_table(
        "reminder_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("reminder_type", sa.String(32), nullable=False, server_default=sa.text("'SMS_BALANCE'")),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'SENT'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_reminder_events_claim_id", "reminder_events", ["claim_id"])

    # appeal_reviews
    op.create_table(
        "appeal_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=False),
        sa.Column("denial_code", sa.String(32), nullable=False),
        sa.Column("ai_recommended_strategy", sa.Text(), nullable=True),
        sa.Column("human_biller_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("draft_appeal_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_appeal_reviews_claim_id", "appeal_reviews", ["claim_id"])

    # human_approval_events
    op.create_table(
        "human_approval_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("justification", sa.String(255), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_human_approval_events_tenant_id", "human_approval_events", ["tenant_id"])

    # auth_rep_consent_events
    op.create_table(
        "auth_rep_consent_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("authorized_by", sa.String(255), nullable=True),
        sa.Column("relationship", sa.String(64), nullable=True),
        sa.Column("consent_scope", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_auth_rep_consent_events_patient_id", "auth_rep_consent_events", ["patient_id"])
    op.create_index("ix_auth_rep_consent_events_tenant_id", "auth_rep_consent_events", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("auth_rep_consent_events")
    op.drop_table("human_approval_events")
    op.drop_table("appeal_reviews")
    op.drop_table("reminder_events")
    op.drop_table("claim_audit_events")
    op.drop_table("collections_reviews")
    op.drop_table("payment_link_events")
    op.drop_table("patient_balance_ledger")
    op.drop_table("claim_issues")
