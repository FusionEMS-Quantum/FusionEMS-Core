# pyright: reportAttributeAccessIssue=false
# pylint: disable=no-member
"""centralized billing + sovereign onboarding schema

Revision ID: 20260308_0038
Revises: 20260308_0037
Create Date: 2026-03-08
"""

from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from alembic import op as alembic_op

op = cast(Any, alembic_op)


revision = "20260308_0038"
down_revision = "20260308_0037"
branch_labels = None
depends_on = None


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t LIMIT 1"
        ),
        {"t": table},
    ).first()
    return row is not None


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c LIMIT 1"
        ),
        {"t": table, "c": column},
    ).first()
    return row is not None


def _index_exists(conn, index_name: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = :i LIMIT 1"
        ),
        {"i": index_name},
    ).first()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── onboarding_applications: sovereign intake + mode forks ──────────────────
    onboarding_cols = [
        ("npi_number", "TEXT"),
        ("operational_mode", "TEXT"),
        ("billing_mode", "TEXT"),
        ("primary_tail_number", "TEXT"),
        ("base_icao", "TEXT"),
        ("billing_contact_name", "TEXT"),
        ("billing_contact_email", "TEXT"),
        ("implementation_owner_name", "TEXT"),
        ("implementation_owner_email", "TEXT"),
        ("identity_sso_preference", "TEXT"),
        ("policy_flags", "JSONB DEFAULT '{}'::jsonb"),
        ("statement_prefix", "TEXT"),
        ("provisioning_status", "TEXT DEFAULT 'pending'"),
        ("provisioning_steps", "JSONB DEFAULT '[]'::jsonb"),
        ("provisioning_error", "TEXT"),
    ]
    for col_name, col_type in onboarding_cols:
        if not _column_exists(conn, "onboarding_applications", col_name):
            op.execute(
                sa.text(
                    f"ALTER TABLE onboarding_applications ADD COLUMN {col_name} {col_type}"
                )
            )

    # Data backfill defaults for existing rows
    op.execute(
        sa.text(
            "UPDATE onboarding_applications "
            "SET billing_mode = COALESCE(NULLIF(billing_mode, ''), 'FUSION_RCM'), "
            "operational_mode = COALESCE(NULLIF(operational_mode, ''), 'EMS_TRANSPORT'), "
            "provisioning_status = COALESCE(NULLIF(provisioning_status, ''), "
            "CASE "
            "  WHEN status IN ('provisioned', 'active') THEN 'complete' "
            "  WHEN status IN ('payment_pending', 'legal_pending') THEN 'processing' "
            "  ELSE 'pending' END)"
        )
    )

    if not _index_exists(conn, "ix_onboarding_apps_billing_mode"):
        op.execute(
            "CREATE INDEX ix_onboarding_apps_billing_mode ON onboarding_applications (billing_mode)"
        )
    if not _index_exists(conn, "ix_onboarding_apps_operational_mode"):
        op.execute(
            "CREATE INDEX ix_onboarding_apps_operational_mode ON onboarding_applications (operational_mode)"
        )

    # ── central_billing_lines: single-number canonical config ───────────────────
    if not _table_exists(conn, "central_billing_lines"):
        op.execute(
            """
            CREATE TABLE central_billing_lines (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                line_label TEXT NOT NULL DEFAULT 'FusionEMS Central Billing',
                phone_e164 TEXT NOT NULL UNIQUE,
                telnyx_connection_id TEXT,
                telnyx_number_id TEXT,
                is_active BOOLEAN NOT NULL DEFAULT true,
                purchased_at TIMESTAMPTZ,
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    # ── tenant_billing_modes ─────────────────────────────────────────────────────
    if not _table_exists(conn, "tenant_billing_modes"):
        op.execute(
            """
            CREATE TABLE tenant_billing_modes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                billing_mode TEXT NOT NULL,
                operational_mode TEXT NOT NULL,
                centralized_voice_enabled BOOLEAN NOT NULL DEFAULT false,
                statement_prefix TEXT,
                configured_by_user_id UUID,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_tenant_billing_mode UNIQUE (tenant_id)
            )
            """
        )
    if not _index_exists(conn, "ix_tenant_billing_modes_mode"):
        op.execute(
            "CREATE INDEX ix_tenant_billing_modes_mode ON tenant_billing_modes (billing_mode, operational_mode)"
        )

    # ── billing_phone_policies ───────────────────────────────────────────────────
    if not _table_exists(conn, "billing_phone_policies"):
        op.execute(
            """
            CREATE TABLE billing_phone_policies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                billing_mode TEXT NOT NULL,
                allow_ai_balance_inquiry BOOLEAN NOT NULL DEFAULT true,
                allow_ai_payment_link_resend BOOLEAN NOT NULL DEFAULT true,
                allow_ai_statement_resend BOOLEAN NOT NULL DEFAULT true,
                allow_ai_address_confirmation BOOLEAN NOT NULL DEFAULT false,
                allow_ai_payment_plan_intake BOOLEAN NOT NULL DEFAULT false,
                collections_enabled BOOLEAN NOT NULL DEFAULT false,
                debt_setoff_enabled BOOLEAN NOT NULL DEFAULT false,
                require_human_for_disputes BOOLEAN NOT NULL DEFAULT true,
                require_human_for_legal_threat BOOLEAN NOT NULL DEFAULT true,
                escalation_priority TEXT NOT NULL DEFAULT 'normal',
                policy_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_billing_phone_policy_tenant UNIQUE (tenant_id)
            )
            """
        )
    if not _index_exists(conn, "ix_billing_phone_policies_tenant"):
        op.execute(
            "CREATE INDEX ix_billing_phone_policies_tenant ON billing_phone_policies (tenant_id)"
        )

    # ── billing_voice_sessions ───────────────────────────────────────────────────
    if not _table_exists(conn, "billing_voice_sessions"):
        op.execute(
            """
            CREATE TABLE billing_voice_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id TEXT NOT NULL UNIQUE,
                call_control_id TEXT NOT NULL,
                caller_phone_number TEXT,
                central_line_phone TEXT,
                tenant_id UUID,
                statement_id TEXT,
                account_id TEXT,
                responsible_party_id UUID,
                verification_state TEXT NOT NULL DEFAULT 'LOOKUP_PENDING',
                state TEXT NOT NULL DEFAULT 'CALL_RECEIVED',
                ai_intent TEXT,
                ai_confidence NUMERIC(5,4),
                ai_summary TEXT,
                handoff_required BOOLEAN NOT NULL DEFAULT false,
                handoff_reason TEXT,
                closed_reason TEXT,
                started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ended_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_voice_sessions_lookup"):
        op.execute(
            "CREATE INDEX ix_billing_voice_sessions_lookup ON billing_voice_sessions (tenant_id, statement_id, account_id, state)"
        )

    # ── billing_call_intents ─────────────────────────────────────────────────────
    if not _table_exists(conn, "billing_call_intents"):
        op.execute(
            """
            CREATE TABLE billing_call_intents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL,
                intent_code TEXT NOT NULL,
                confidence NUMERIC(5,4),
                extracted_entities JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_call_intents_session"):
        op.execute("CREATE INDEX ix_billing_call_intents_session ON billing_call_intents (session_id, created_at)")

    # ── billing_call_escalations ────────────────────────────────────────────────
    if not _table_exists(conn, "billing_call_escalations"):
        op.execute(
            """
            CREATE TABLE billing_call_escalations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL,
                tenant_id UUID,
                caller_phone_number TEXT,
                statement_id TEXT,
                account_id TEXT,
                ai_summary TEXT,
                escalation_reason TEXT NOT NULL,
                recommended_next_action TEXT,
                status TEXT NOT NULL DEFAULT 'awaiting_human',
                taken_by_user_id UUID,
                taken_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_call_escalations_status"):
        op.execute("CREATE INDEX ix_billing_call_escalations_status ON billing_call_escalations (status, created_at)")

    # ── human_takeovers ─────────────────────────────────────────────────────────
    if not _table_exists(conn, "human_takeovers"):
        op.execute(
            """
            CREATE TABLE human_takeovers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL,
                escalation_id UUID,
                founder_user_id UUID,
                takeover_channel TEXT NOT NULL DEFAULT 'softphone',
                takeover_state TEXT NOT NULL DEFAULT 'connected',
                notes TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    # ── voice_automation_audit_events ─────────────────────────────────────────
    if not _table_exists(conn, "voice_automation_audit_events"):
        op.execute(
            """
            CREATE TABLE voice_automation_audit_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID,
                tenant_id UUID,
                event_type TEXT NOT NULL,
                event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                risk_level TEXT,
                correlation_id TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_voice_automation_audit_events_tenant"):
        op.execute(
            "CREATE INDEX ix_voice_automation_audit_events_tenant ON voice_automation_audit_events (tenant_id, event_type, created_at)"
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS voice_automation_audit_events CASCADE")
    op.execute("DROP TABLE IF EXISTS human_takeovers CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_call_escalations CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_call_intents CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voice_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_phone_policies CASCADE")
    op.execute("DROP TABLE IF EXISTS tenant_billing_modes CASCADE")
    op.execute("DROP TABLE IF EXISTS central_billing_lines CASCADE")

    # Keep downgrade conservative for shared onboarding table; only remove newly added cols if present.
    conn = op.get_bind()
    for col in [
        "provisioning_error",
        "provisioning_steps",
        "provisioning_status",
        "statement_prefix",
        "policy_flags",
        "identity_sso_preference",
        "implementation_owner_email",
        "implementation_owner_name",
        "billing_contact_email",
        "billing_contact_name",
        "base_icao",
        "primary_tail_number",
        "billing_mode",
        "operational_mode",
        "npi_number",
    ]:
        if _column_exists(conn, "onboarding_applications", col):
            op.execute(sa.text(f"ALTER TABLE onboarding_applications DROP COLUMN {col}"))
