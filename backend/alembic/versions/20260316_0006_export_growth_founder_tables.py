"""Add export/offboarding, growth, and founder tax tables

Revision ID: 20260316_0006
Revises: 20260316_0005
Create Date: 2026-03-16 00:06:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0006"
down_revision = "20260316_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Export / Offboarding ──────────────────────────────────────────────────

    # offboarding_requests (must exist before export_packages due to FK)
    op.create_table(
        "offboarding_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default=sa.text("'REQUESTED'")),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("target_vendor", sa.String(255), nullable=True),
        sa.Column("requested_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_method", sa.String(32), nullable=False, server_default=sa.text("'SECURE_LINK'")),
        sa.Column("delivery_target", sa.String(512), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("risk_level", sa.String(32), nullable=True),
        sa.Column("risk_details", JSONB(), nullable=True),
        sa.Column("requested_by", UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_offboarding_requests_tenant_id", "offboarding_requests", ["tenant_id"])
    op.create_index("ix_offboarding_requests_state", "offboarding_requests", ["state"])

    # export_packages
    op.create_table(
        "export_packages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("offboarding_id", UUID(as_uuid=True),
                  sa.ForeignKey("offboarding_requests.id"), nullable=True),
        sa.Column("state", sa.String(32), nullable=False, server_default=sa.text("'REQUESTED'")),
        sa.Column("modules", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("date_range_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_range_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("patient_scope", JSONB(), nullable=True),
        sa.Column("account_scope", JSONB(), nullable=True),
        sa.Column("include_attachments", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("include_field_crosswalk", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("delivery_method", sa.String(32), nullable=False, server_default=sa.text("'SECURE_LINK'")),
        sa.Column("delivery_target", sa.String(512), nullable=True),
        sa.Column("requested_by", UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("package_s3_key", sa.String(512), nullable=True),
        sa.Column("manifest", JSONB(), nullable=True),
        sa.Column("integrity_hash", sa.String(128), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column("total_size_bytes", sa.Integer(), nullable=True),
        sa.Column("secure_link_token", sa.String(256), nullable=True),
        sa.Column("secure_link_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("secure_link_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("risk_level", sa.String(32), nullable=True),
        sa.Column("risk_details", JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_export_packages_tenant_id", "export_packages", ["tenant_id"])
    op.create_index("ix_export_packages_state", "export_packages", ["state"])

    # export_access_logs
    op.create_table(
        "export_access_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("package_id", UUID(as_uuid=True), sa.ForeignKey("export_packages.id"), nullable=False),
        sa.Column("accessed_by", UUID(as_uuid=True), nullable=False),
        sa.Column("access_type", sa.String(32), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_export_access_logs_package_id", "export_access_logs", ["package_id"])

    # third_party_billers
    op.create_table(
        "third_party_billers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("biller_name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(32), nullable=True),
        sa.Column("portal_access_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("access_role", sa.String(32), nullable=False, server_default=sa.text("'billing'")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_third_party_billers_tenant_id", "third_party_billers", ["tenant_id"])

    # ── Growth ────────────────────────────────────────────────────────────────

    # growth_campaigns
    op.create_table(
        "growth_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("objective", sa.String(255), nullable=True),
        sa.Column("audience", JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
    )
    op.create_index("ix_growth_campaigns_tenant_id", "growth_campaigns", ["tenant_id"])
    op.create_index("ix_growth_campaigns_name", "growth_campaigns", ["name"])

    # growth_social_posts
    op.create_table(
        "growth_social_posts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("growth_campaigns.id"), nullable=True),
        sa.Column("platform", sa.String(64), nullable=True),
        sa.Column("content", sa.String(4096), nullable=True),
        sa.Column("media_urls", JSONB(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("post_metrics", JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
    )
    op.create_index("ix_growth_social_posts_tenant_id", "growth_social_posts", ["tenant_id"])

    # growth_demo_assets
    op.create_table(
        "growth_demo_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("growth_campaigns.id"), nullable=True),
        sa.Column("asset_type", sa.String(64), nullable=True),
        sa.Column("content_url", sa.String(1024), nullable=True),
        sa.Column("asset_metadata", JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
    )
    op.create_index("ix_growth_demo_assets_tenant_id", "growth_demo_assets", ["tenant_id"])

    # growth_landing_pages
    op.create_table(
        "growth_landing_pages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("slug", sa.String(255), nullable=True, unique=True),
        sa.Column("campaign_id", sa.String(36), sa.ForeignKey("growth_campaigns.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("config", JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("conversions", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
    )
    op.create_index("ix_growth_landing_pages_tenant_id", "growth_landing_pages", ["tenant_id"])

    # growth_automations
    op.create_table(
        "growth_automations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("trigger_type", sa.String(64), nullable=True),
        sa.Column("flow_schema", JSONB(), nullable=True, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.text("now()")),
    )
    op.create_index("ix_growth_automations_tenant_id", "growth_automations", ["tenant_id"])

    # ── Founder Tax ────────────────────────────────────────────────────────────

    # tax_document_vault
    op.create_table(
        "tax_document_vault",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("bucket_classification", sa.String(50), nullable=False,
                  server_default=sa.text("'BUSINESS_LLC'")),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("document_name", sa.String(255), nullable=False),
        sa.Column("aws_s3_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("aws_bucket_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("is_encrypted_at_rest", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ai_tags", JSONB(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tax_document_vault_tax_year", "tax_document_vault", ["tax_year"])
    op.create_index("ix_tax_document_vault_document_type", "tax_document_vault", ["document_type"])

    # quantum_temporal_ledger
    op.create_table(
        "quantum_temporal_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("debit_account", sa.String(100), nullable=False),
        sa.Column("credit_account", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("is_reversing_entry", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("original_entry_id_if_reversed", UUID(as_uuid=True),
                  sa.ForeignKey("quantum_temporal_ledger.id"), nullable=True),
        sa.Column("audit_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_quantum_temporal_ledger_entry_date", "quantum_temporal_ledger", ["entry_date"])

    # founder_expenses
    op.create_table(
        "founder_expenses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("merchant_name", sa.String(255), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("irs_category", sa.String(100), nullable=True),
        sa.Column("business_purpose", sa.String(500), nullable=True),
        sa.Column("is_home_office_prorated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_startup_expense_sec195", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("payment_source", sa.String(50), nullable=False, server_default=sa.text("'BUSINESS_CREDIT'")),
        sa.Column("is_owner_capital_contribution", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("reimbursed_via_accountable_plan", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("receipt_image_url", sa.String(1024), nullable=True),
        sa.Column("ai_confidence_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("ai_raw_ocr_data", JSONB(), nullable=True),
        sa.Column("human_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_founder_expenses_merchant_name", "founder_expenses", ["merchant_name"])
    op.create_index("ix_founder_expenses_transaction_date", "founder_expenses", ["transaction_date"])

    # tax_filing_transmissions
    op.create_table(
        "tax_filing_transmissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("form_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("compiled_tax_payload", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("irs_submission_id", sa.String(100), nullable=True),
        sa.Column("rejection_errors", JSONB(), nullable=True),
        sa.Column("realtime_efile_status_message", sa.String(255), nullable=True),
        sa.Column("last_irs_status_check_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # realtime_tax_strategies
    op.create_table(
        "realtime_tax_strategies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("strategy_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_savings", sa.Float(), nullable=True),
        sa.Column("risk_level", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("realtime_tax_strategies")
    op.drop_table("tax_filing_transmissions")
    op.drop_table("founder_expenses")
    op.drop_table("quantum_temporal_ledger")
    op.drop_table("tax_document_vault")
    op.drop_table("growth_automations")
    op.drop_table("growth_landing_pages")
    op.drop_table("growth_demo_assets")
    op.drop_table("growth_social_posts")
    op.drop_table("growth_campaigns")
    op.drop_table("third_party_billers")
    op.drop_table("export_access_logs")
    op.drop_table("export_packages")
    op.drop_table("offboarding_requests")
