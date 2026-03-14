"""Add agency extension policy tables

Revision ID: 20260316_0002
Revises: 20260316_0001
Create Date: 2026-03-16 00:02:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260316_0002"
down_revision = "20260316_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agency_billing_policies
    op.create_table(
        "agency_billing_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("patient_billing_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("patient_self_pay_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("internal_follow_up_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("third_party_collections_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("payment_plans_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("state_debt_setoff_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("min_balance_for_statement", sa.Integer(), nullable=False, server_default=sa.text("500")),
        sa.Column("days_until_collections", sa.Integer(), nullable=False, server_default=sa.text("120")),
        sa.Column("grace_period_days", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # agency_collections_policies
    op.create_table(
        "agency_collections_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("min_debt_amount_cents", sa.Integer(), nullable=False, server_default=sa.text("5000")),
        sa.Column("vendor_name", sa.String(128), nullable=True),
        sa.Column("auto_escalate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # agency_tax_profiles
    op.create_table(
        "agency_tax_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("ein", sa.String(20), nullable=True),
        sa.Column("state_tax_id", sa.String(64), nullable=True),
        sa.Column("tax_exempt", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("tax_exempt_certificate_ref", sa.String(255), nullable=True),
        sa.Column("filing_state", sa.String(2), nullable=True),
        sa.Column("w9_on_file", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # agency_reminder_policies
    op.create_table(
        "agency_reminder_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("reminder_cadence_days", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("max_reminders", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("mail_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("escalate_after_final", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("escalation_action", sa.String(32), nullable=False, server_default=sa.text("'COLLECTIONS_REVIEW'")),
        sa.Column("quiet_hours_start", sa.Integer(), nullable=True),
        sa.Column("quiet_hours_end", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # agency_public_sector_profiles
    op.create_table(
        "agency_public_sector_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("tax_id", sa.String(64), nullable=True),
        sa.Column("legal_name", sa.String(255), nullable=False),
        sa.Column("is_municipality", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("state_entity_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("agency_public_sector_profiles")
    op.drop_table("agency_reminder_policies")
    op.drop_table("agency_tax_profiles")
    op.drop_table("agency_collections_policies")
    op.drop_table("agency_billing_policies")
