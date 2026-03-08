"""centralized billing communications workflows schema

Revision ID: 20260308_0039
Revises: 20260308_0038
Create Date: 2026-03-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260308_0039"
down_revision = "20260308_0038"
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

    if not _table_exists(conn, "billing_calls"):
        op.execute(
            """
            CREATE TABLE billing_calls (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID,
                call_control_id TEXT NOT NULL,
                tenant_id UUID,
                caller_phone_number TEXT,
                central_line_phone TEXT,
                statement_id TEXT,
                account_id TEXT,
                verification_state TEXT,
                state TEXT NOT NULL DEFAULT 'CALL_RECEIVED',
                started_at TIMESTAMPTZ,
                ended_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_calls_lookup"):
        op.execute(
            "CREATE INDEX ix_billing_calls_lookup ON billing_calls (tenant_id, statement_id, account_id, state, created_at)"
        )

    if not _table_exists(conn, "billing_call_transcripts"):
        op.execute(
            """
            CREATE TABLE billing_call_transcripts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                call_id UUID,
                session_id UUID,
                transcript_text TEXT,
                source_engine TEXT,
                confidence NUMERIC(5,4),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_call_summaries"):
        op.execute(
            """
            CREATE TABLE billing_call_summaries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                call_id UUID,
                session_id UUID,
                summary_text TEXT NOT NULL,
                intent_code TEXT,
                recommended_next_action TEXT,
                confidence NUMERIC(5,4),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_verification_states"):
        op.execute(
            """
            CREATE TABLE billing_verification_states (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                call_id UUID,
                session_id UUID,
                verification_state TEXT NOT NULL,
                verification_method TEXT,
                verification_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_sms_threads"):
        op.execute(
            """
            CREATE TABLE billing_sms_threads (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID,
                central_phone TEXT NOT NULL,
                participant_phone TEXT NOT NULL,
                statement_id TEXT,
                account_id TEXT,
                state TEXT NOT NULL DEFAULT 'SMS_CREATED',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_sms_threads_lookup"):
        op.execute(
            "CREATE INDEX ix_billing_sms_threads_lookup ON billing_sms_threads (central_phone, participant_phone, tenant_id, state, updated_at)"
        )

    if not _table_exists(conn, "billing_sms_messages"):
        op.execute(
            """
            CREATE TABLE billing_sms_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                thread_id UUID,
                message_id TEXT,
                direction TEXT NOT NULL,
                from_phone TEXT NOT NULL,
                to_phone TEXT NOT NULL,
                body TEXT,
                state TEXT NOT NULL DEFAULT 'SMS_CREATED',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_sms_messages_thread"):
        op.execute(
            "CREATE INDEX ix_billing_sms_messages_thread ON billing_sms_messages (thread_id, created_at)"
        )

    if not _table_exists(conn, "billing_sms_delivery_events"):
        op.execute(
            """
            CREATE TABLE billing_sms_delivery_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                message_id TEXT,
                thread_id UUID,
                delivery_state TEXT NOT NULL,
                provider_event_id TEXT,
                provider_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_voicemails"):
        op.execute(
            """
            CREATE TABLE billing_voicemails (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                call_control_id TEXT,
                tenant_id UUID,
                caller_phone_number TEXT,
                central_line_phone TEXT,
                statement_id TEXT,
                account_id TEXT,
                recording_url TEXT,
                state TEXT NOT NULL DEFAULT 'VOICEMAIL_RECEIVED',
                urgency TEXT NOT NULL DEFAULT 'normal',
                risk_level TEXT NOT NULL DEFAULT 'low',
                received_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_voicemails_board"):
        op.execute(
            "CREATE INDEX ix_billing_voicemails_board ON billing_voicemails (state, risk_level, urgency, received_at, created_at)"
        )

    if not _table_exists(conn, "billing_voicemail_transcripts"):
        op.execute(
            """
            CREATE TABLE billing_voicemail_transcripts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voicemail_id UUID,
                engine TEXT,
                transcript_text TEXT,
                confidence NUMERIC(5,4),
                state TEXT NOT NULL DEFAULT 'TRANSCRIBED',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_voicemail_extractions"):
        op.execute(
            """
            CREATE TABLE billing_voicemail_extractions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voicemail_id UUID,
                extracted_statement_id TEXT,
                extracted_account_id TEXT,
                extracted_callback_phone TEXT,
                extraction_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_voicemail_intents"):
        op.execute(
            """
            CREATE TABLE billing_voicemail_intents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voicemail_id UUID,
                intent_code TEXT NOT NULL,
                confidence NUMERIC(5,4),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_voicemail_risk_scores"):
        op.execute(
            """
            CREATE TABLE billing_voicemail_risk_scores (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voicemail_id UUID,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_voicemail_matches"):
        op.execute(
            """
            CREATE TABLE billing_voicemail_matches (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voicemail_id UUID,
                tenant_id UUID,
                statement_id TEXT,
                account_id TEXT,
                match_confidence NUMERIC(5,4),
                state TEXT NOT NULL DEFAULT 'MATCH_PENDING',
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_voicemail_escalations"):
        op.execute(
            """
            CREATE TABLE billing_voicemail_escalations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voicemail_id UUID,
                escalation_reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_human',
                taken_by_user_id UUID,
                taken_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_callback_tasks"):
        op.execute(
            """
            CREATE TABLE billing_callback_tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                voicemail_id UUID,
                tenant_id UUID,
                callback_phone TEXT,
                callback_state TEXT NOT NULL DEFAULT 'CALLBACK_TASK_CREATED',
                sla_due_at TIMESTAMPTZ,
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ,
                priority TEXT NOT NULL DEFAULT 'normal',
                reason TEXT,
                assigned_user_id UUID,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    if not _index_exists(conn, "ix_billing_callback_tasks_sla"):
        op.execute(
            "CREATE INDEX ix_billing_callback_tasks_sla ON billing_callback_tasks (callback_state, sla_due_at, priority, created_at)"
        )

    if not _table_exists(conn, "billing_callback_audit_events"):
        op.execute(
            """
            CREATE TABLE billing_callback_audit_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                callback_task_id UUID,
                event_type TEXT NOT NULL,
                event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )

    if not _table_exists(conn, "billing_state_transitions"):
        op.execute(
            """
            CREATE TABLE billing_state_transitions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                object_type TEXT NOT NULL,
                object_id UUID,
                from_state TEXT,
                to_state TEXT NOT NULL,
                reason TEXT,
                actor_type TEXT,
                actor_id UUID,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing_state_transitions CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_callback_audit_events CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_callback_tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voicemail_escalations CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voicemail_matches CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voicemail_risk_scores CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voicemail_intents CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voicemail_extractions CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voicemail_transcripts CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_voicemails CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_sms_delivery_events CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_sms_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_sms_threads CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_verification_states CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_call_summaries CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_call_transcripts CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_calls CASCADE")
