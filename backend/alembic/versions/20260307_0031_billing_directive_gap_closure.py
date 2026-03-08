"""Billing directive gap closure — UsageMeter, BillingInvoiceMirror, agency policies, debt setoff batch/rules

Revision ID: 20260307_0031
Revises: 20260307_0030
Create Date: 2026-03-07

Creates:
  - usage_meters (SaaS metered billing tracking)
  - billing_invoice_mirrors (Stripe invoice local mirror)
  - agency_payment_plan_policies
  - agency_writeoff_policies
  - agency_debt_setoff_policies
  - state_debt_setoff_rule_packs
  - debt_setoff_batches

All tables include RLS policies for tenant isolation.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "20260307_0031"
down_revision: Union[str, None] = "20260307_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    has_tenants = inspector.has_table("tenants")
    has_subscription_items = inspector.has_table("subscription_items")
    has_state_profiles = inspector.has_table("state_debt_setoff_profiles")
    has_setoff_enrollments = inspector.has_table("agency_debt_setoff_enrollments")

    # ── usage_meters ──────────────────────────────────────────────────────────
    if not inspector.has_table("usage_meters"):
        usage_meter_columns = [
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("subscription_item_id", UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("metric_name", sa.String(128), nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
            sa.Column("quantity", sa.Integer, default=0, nullable=False),
            sa.Column("reported_to_stripe", sa.Boolean, default=False, nullable=False),
            sa.Column("stripe_usage_record_id", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        ]
        if has_subscription_items:
            usage_meter_columns.append(sa.ForeignKeyConstraint(["subscription_item_id"], ["subscription_items.id"]))
        if has_tenants:
            usage_meter_columns.append(sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]))
        op.create_table("usage_meters", *usage_meter_columns)
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_meters_tenant_id ON usage_meters (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_meters_sub_item ON usage_meters (subscription_item_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_usage_meters_period ON usage_meters (tenant_id, metric_name, period_start)")

    # ── billing_invoice_mirrors ───────────────────────────────────────────────
    if not inspector.has_table("billing_invoice_mirrors"):
        invoice_mirror_columns = [
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("stripe_invoice_id", sa.String(128), unique=True, nullable=False),
            sa.Column("stripe_subscription_id", sa.String(128), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("amount_due_cents", sa.Integer, default=0, nullable=False),
            sa.Column("amount_paid_cents", sa.Integer, default=0, nullable=False),
            sa.Column("currency", sa.String(3), default="usd", nullable=False),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("line_items_json", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
            sa.Column("hosted_invoice_url", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        ]
        if has_tenants:
            invoice_mirror_columns.append(sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]))
        op.create_table("billing_invoice_mirrors", *invoice_mirror_columns)
    op.execute("CREATE INDEX IF NOT EXISTS ix_billing_invoice_mirrors_tenant_id ON billing_invoice_mirrors (tenant_id)")

    # ── agency_payment_plan_policies ──────────────────────────────────────────
    if not inspector.has_table("agency_payment_plan_policies"):
        payment_policy_columns = [
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), unique=True, nullable=False),
            sa.Column("max_installments", sa.Integer, default=12, nullable=False),
            sa.Column("min_installment_cents", sa.Integer, default=2500, nullable=False),
            sa.Column("interest_rate_bps", sa.Integer, default=0, nullable=False),
            sa.Column("auto_enroll_threshold_cents", sa.Integer, default=10000, nullable=False),
            sa.Column("allow_custom_schedules", sa.Boolean, default=False, nullable=False),
            sa.Column("grace_period_days", sa.Integer, default=15, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        ]
        if has_tenants:
            payment_policy_columns.append(sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]))
        op.create_table("agency_payment_plan_policies", *payment_policy_columns)

    # ── agency_writeoff_policies ──────────────────────────────────────────────
    if not inspector.has_table("agency_writeoff_policies"):
        writeoff_policy_columns = [
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("auto_writeoff_threshold_cents", sa.Integer, default=500, nullable=False),
        sa.Column("max_auto_writeoff_cents", sa.Integer, default=5000, nullable=False),
        sa.Column("require_human_approval_above_cents", sa.Integer, default=5000, nullable=False),
        sa.Column("writeoff_aging_days", sa.Integer, default=365, nullable=False),
        sa.Column("bad_debt_category", sa.String(64), default="UNCOLLECTIBLE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        ]
        if has_tenants:
            writeoff_policy_columns.append(sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]))
        op.create_table("agency_writeoff_policies", *writeoff_policy_columns)

    # ── agency_debt_setoff_policies ───────────────────────────────────────────
    if not inspector.has_table("agency_debt_setoff_policies"):
        setoff_policy_columns = [
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("enabled", sa.Boolean, default=False, nullable=False),
        sa.Column("min_debt_cents", sa.Integer, default=5000, nullable=False),
        sa.Column("min_aging_days", sa.Integer, default=90, nullable=False),
        sa.Column("exclude_payment_plan_active", sa.Boolean, default=True, nullable=False),
        sa.Column("exclude_appeal_in_progress", sa.Boolean, default=True, nullable=False),
        sa.Column("max_submissions_per_batch", sa.Integer, default=500, nullable=False),
        sa.Column("require_human_review", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        ]
        if has_tenants:
            setoff_policy_columns.append(sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]))
        op.create_table("agency_debt_setoff_policies", *setoff_policy_columns)

    # ── state_debt_setoff_rule_packs ──────────────────────────────────────────
    if not inspector.has_table("state_debt_setoff_rule_packs"):
        rule_pack_columns = [
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("state_profile_id", UUID(as_uuid=True), unique=True, nullable=False),
        sa.Column("notice_required_days", sa.Integer, default=30, nullable=False),
        sa.Column("max_offset_pct", sa.Integer, default=100, nullable=False),
        sa.Column("hardship_exemption_enabled", sa.Boolean, default=False, nullable=False),
        sa.Column("appeal_window_days", sa.Integer, default=30, nullable=False),
        sa.Column("eligible_refund_types", JSONB, server_default=sa.text("'[\"income_tax\"]'::jsonb"), nullable=False),
        sa.Column("submission_format", sa.String(64), default="CSV_STANDARD", nullable=False),
        sa.Column("required_fields", JSONB, server_default=sa.text("'[\"ssn\",\"full_name\",\"debt_amount\",\"account_number\"]'::jsonb"), nullable=False),
        sa.Column("statute_reference", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        ]
        if has_state_profiles:
            rule_pack_columns.append(sa.ForeignKeyConstraint(["state_profile_id"], ["state_debt_setoff_profiles.id"]))
        op.create_table("state_debt_setoff_rule_packs", *rule_pack_columns)

    # ── debt_setoff_batches ───────────────────────────────────────────────────
    if not inspector.has_table("debt_setoff_batches"):
        debt_batch_columns = [
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("enrollment_id", UUID(as_uuid=True), nullable=False),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("batch_reference", sa.String(128), unique=True, nullable=False),
        sa.Column("record_count", sa.Integer, default=0, nullable=False),
        sa.Column("total_amount_cents", sa.Integer, default=0, nullable=False),
        sa.Column("status", sa.String(32), default="PENDING", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("export_file_key", sa.String(512), nullable=True),
        sa.Column("response_file_key", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        ]
        if has_setoff_enrollments:
            debt_batch_columns.append(sa.ForeignKeyConstraint(["enrollment_id"], ["agency_debt_setoff_enrollments.id"]))
        if has_tenants:
            debt_batch_columns.append(sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]))
        op.create_table("debt_setoff_batches", *debt_batch_columns)
    op.execute("CREATE INDEX IF NOT EXISTS ix_debt_setoff_batches_tenant_id ON debt_setoff_batches (tenant_id)")

    # ── RLS Policies ──────────────────────────────────────────────────────────
    _rls_tables = [
        "usage_meters",
        "billing_invoice_mirrors",
        "agency_payment_plan_policies",
        "agency_writeoff_policies",
        "agency_debt_setoff_policies",
        "debt_setoff_batches",
    ]
    for table in _rls_tables:
        if not inspector.has_table(table):
            continue
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.current_tenant_id')::uuid)"
        )

    # state_debt_setoff_rule_packs is platform-level (no tenant_id), no RLS needed


def downgrade() -> None:
    op.drop_table("debt_setoff_batches")
    op.drop_table("state_debt_setoff_rule_packs")
    op.drop_table("agency_debt_setoff_policies")
    op.drop_table("agency_writeoff_policies")
    op.drop_table("agency_payment_plan_policies")
    op.drop_table("billing_invoice_mirrors")
    op.drop_table("usage_meters")
