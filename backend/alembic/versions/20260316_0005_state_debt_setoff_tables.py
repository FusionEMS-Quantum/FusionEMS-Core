"""Add state debt setoff domain tables

Revision ID: 20260316_0005
Revises: 20260316_0004
Create Date: 2026-03-16 00:05:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0005"
down_revision = "20260316_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # state_debt_setoff_profiles
    op.create_table(
        "state_debt_setoff_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("state_code", sa.String(2), nullable=False, unique=True),
        sa.Column("program_name", sa.String(255), nullable=False),
        sa.Column("min_debt_amount_cents", sa.Integer(), nullable=False, server_default=sa.text("5000")),
        sa.Column("min_days_delinquent", sa.Integer(), nullable=False, server_default=sa.text("60")),
        sa.Column("eligible_agency_types", JSONB(), nullable=False,
                  server_default=sa.text("'[\"MUNICIPALITY\",\"COUNTY\",\"HOSPITAL_DISTRICT\"]'")),
        sa.Column("export_format", sa.String(64), nullable=False, server_default=sa.text("'CSV_STANDARD'")),
        sa.Column("submission_frequency", sa.String(32), nullable=False, server_default=sa.text("'ANNUAL'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # agency_debt_setoff_enrollments
    op.create_table(
        "agency_debt_setoff_enrollments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("state_profile_id", UUID(as_uuid=True),
                  sa.ForeignKey("state_debt_setoff_profiles.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("enrollment_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tax_id_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("agreement_signed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # debt_setoff_submissions
    op.create_table(
        "debt_setoff_submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("enrollment_id", UUID(as_uuid=True),
                  sa.ForeignKey("agency_debt_setoff_enrollments.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("claim_id", UUID(as_uuid=True), nullable=True),
        sa.Column("amount_submitted_cents", sa.Integer(), nullable=False),
        sa.Column("submission_batch_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'SUBMITTED'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_debt_setoff_submissions_enrollment_id", "debt_setoff_submissions", ["enrollment_id"])
    op.create_index("ix_debt_setoff_submissions_patient_id", "debt_setoff_submissions", ["patient_id"])

    # debt_setoff_responses
    op.create_table(
        "debt_setoff_responses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", UUID(as_uuid=True),
                  sa.ForeignKey("debt_setoff_submissions.id"), nullable=False),
        sa.Column("response_code", sa.String(64), nullable=True),
        sa.Column("amount_offset_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_debt_setoff_responses_submission_id", "debt_setoff_responses", ["submission_id"])

    # debt_setoff_notice_records
    op.create_table(
        "debt_setoff_notice_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", UUID(as_uuid=True),
                  sa.ForeignKey("debt_setoff_submissions.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("notice_type", sa.String(32), nullable=False),
        sa.Column("sent_via", sa.String(16), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_status", sa.String(32), nullable=False, server_default=sa.text("'SENT'")),
        sa.Column("required_response_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_received", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("dispute_filed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("lob_tracking_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_debt_setoff_notice_records_submission_id", "debt_setoff_notice_records", ["submission_id"])
    op.create_index("ix_debt_setoff_notice_records_tenant_id", "debt_setoff_notice_records", ["tenant_id"])

    # debt_setoff_eligibility_decisions
    op.create_table(
        "debt_setoff_eligibility_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("enrollment_id", UUID(as_uuid=True),
                  sa.ForeignKey("agency_debt_setoff_enrollments.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("claim_id", UUID(as_uuid=True), nullable=True),
        sa.Column("eligible", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("debt_amount_cents", sa.Integer(), nullable=False),
        sa.Column("debt_aging_days", sa.Integer(), nullable=False),
        sa.Column("rule_pack_version", sa.String(64), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("override_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("override_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_debt_setoff_eligibility_decisions_enrollment_id",
                    "debt_setoff_eligibility_decisions", ["enrollment_id"])

    # debt_setoff_recovery_records
    op.create_table(
        "debt_setoff_recovery_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", UUID(as_uuid=True),
                  sa.ForeignKey("debt_setoff_submissions.id"), nullable=False),
        sa.Column("response_id", UUID(as_uuid=True),
                  sa.ForeignKey("debt_setoff_responses.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("amount_recovered_cents", sa.Integer(), nullable=False),
        sa.Column("recovery_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_to_claim_id", UUID(as_uuid=True), nullable=True),
        sa.Column("applied_to_patient_id", UUID(as_uuid=True),
                  sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("ledger_entry_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reconciled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_debt_setoff_recovery_records_submission_id", "debt_setoff_recovery_records", ["submission_id"])
    op.create_index("ix_debt_setoff_recovery_records_tenant_id", "debt_setoff_recovery_records", ["tenant_id"])

    # debt_setoff_reversal_records
    op.create_table(
        "debt_setoff_reversal_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("submission_id", UUID(as_uuid=True),
                  sa.ForeignKey("debt_setoff_submissions.id"), nullable=False),
        sa.Column("recovery_id", UUID(as_uuid=True),
                  sa.ForeignKey("debt_setoff_recovery_records.id"), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("reversal_reason", sa.String(64), nullable=False),
        sa.Column("amount_reversed_cents", sa.Integer(), nullable=False),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state_reference_id", sa.String(128), nullable=True),
        sa.Column("ledger_adjustment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_debt_setoff_reversal_records_submission_id", "debt_setoff_reversal_records", ["submission_id"])
    op.create_index("ix_debt_setoff_reversal_records_tenant_id", "debt_setoff_reversal_records", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("debt_setoff_reversal_records")
    op.drop_table("debt_setoff_recovery_records")
    op.drop_table("debt_setoff_eligibility_decisions")
    op.drop_table("debt_setoff_notice_records")
    op.drop_table("debt_setoff_responses")
    op.drop_table("debt_setoff_submissions")
    op.drop_table("agency_debt_setoff_enrollments")
    op.drop_table("state_debt_setoff_profiles")
