"""billing communications tables: sms log, opt-outs, mail fulfillment records

Revision ID: 20260307_0028
Revises: 20260307_0027
Create Date: 2026-03-07

Tables:
  billing_sms_log        — audit log for every Telnyx billing SMS send attempt
  billing_sms_opt_outs   — opt-out/STOP management per tenant+phone
  mail_fulfillment_records — LOB physical mail send log

These tables support the BillingCommunicationService billing-only rail.
Telnyx is billing-only; CrewLink is ops paging only. These tables enforce that boundary.
"""
from __future__ import annotations

from alembic import op


revision = "20260307_0028"
down_revision = "20260307_0027"
branch_labels = None
depends_on = None


def _table_exists(conn, name: str) -> bool:
    r = conn.execute(
        __import__("sqlalchemy").text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t)"
        ),
        {"t": name},
    )
    return r.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    # ── billing_sms_log ───────────────────────────────────────────────────────
    # Every Telnyx billing SMS attempt — queued, sent, failed, opted-out.
    if not _table_exists(conn, "billing_sms_log"):
        op.execute("""
            CREATE TABLE billing_sms_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                patient_id TEXT,
                to_phone TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED',
                dedup_key TEXT,
                telnyx_message_id TEXT,
                error_detail TEXT,
                correlation_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_billing_sms_log_tenant_id "
            "ON billing_sms_log (tenant_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_billing_sms_log_patient_id "
            "ON billing_sms_log (patient_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_billing_sms_log_dedup_key "
            "ON billing_sms_log (tenant_id, dedup_key)"
        )

    # Note: opt-out management uses existing telnyx_opt_outs table (created in 0010)
    # billing_communications_service.py reads/writes telnyx_opt_outs directly.

    # ── mail_fulfillment_records ──────────────────────────────────────────────
    # LOB physical mail sends — statements, collection notices, cover letters.
    if not _table_exists(conn, "mail_fulfillment_records"):
        op.execute("""
            CREATE TABLE mail_fulfillment_records (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                claim_id TEXT NOT NULL,
                template_id TEXT NOT NULL DEFAULT 'STATEMENT_V1',
                recipient_name TEXT,
                address_line1 TEXT,
                address_line2 TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                lob_letter_id TEXT,
                status TEXT NOT NULL DEFAULT 'CREATED',
                error_detail TEXT,
                correlation_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_mail_fulfillment_records_tenant_id "
            "ON mail_fulfillment_records (tenant_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_mail_fulfillment_records_claim_id "
            "ON mail_fulfillment_records (claim_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_mail_fulfillment_records_lob_id "
            "ON mail_fulfillment_records (lob_letter_id)"
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS mail_fulfillment_records CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_sms_log CASCADE")
