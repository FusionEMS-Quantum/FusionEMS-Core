"""Add communication domain tables

Revision ID: 20260316_0003
Revises: 20260316_0002
Create Date: 2026-03-16 00:03:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0003"
down_revision = "20260316_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agency_phone_numbers
    op.create_table(
        "agency_phone_numbers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False, unique=True),
        sa.Column("telnyx_phone_number_id", sa.String(128), nullable=False, unique=True),
        sa.Column("voice_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fax_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_agency_phone_numbers_tenant_id", "agency_phone_numbers", ["tenant_id"])

    # communication_threads
    op.create_table(
        "communication_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("channel", sa.String(16), nullable=False, server_default=sa.text("'SMS'")),
        sa.Column("topic", sa.String(32), nullable=False, server_default=sa.text("'BILLING_GENERAL'")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'THREAD_CREATED'")),
        sa.Column("latest_message_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_communication_threads_tenant_id", "communication_threads", ["tenant_id"])
    op.create_index("ix_communication_threads_patient_id", "communication_threads", ["patient_id"])

    # communication_messages
    op.create_table(
        "communication_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("communication_threads.id"), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sender_type", sa.String(16), nullable=False, server_default=sa.text("'SYSTEM'")),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("telnyx_message_id", sa.String(128), nullable=True, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default=sa.text("'SENT'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_communication_messages_thread_id", "communication_messages", ["thread_id"])

    # telecom_provisioning_runs
    op.create_table(
        "telecom_provisioning_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("requested_quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("provisioned_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("telnyx_order_id", sa.String(128), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_telecom_provisioning_runs_tenant_id", "telecom_provisioning_runs", ["tenant_id"])

    # communication_delivery_events
    op.create_table(
        "communication_delivery_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("communication_messages.id"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.String(128), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_communication_delivery_events_message_id", "communication_delivery_events", ["message_id"])

    # communication_templates
    op.create_table(
        "communication_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("variables", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_communication_templates_tenant_id", "communication_templates", ["tenant_id"])

    # communication_policies
    op.create_table(
        "communication_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("sms_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("voice_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("fax_allowed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mail_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ai_auto_reply_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("quiet_hours_start", sa.Integer(), nullable=True),
        sa.Column("quiet_hours_end", sa.Integer(), nullable=True),
        sa.Column("max_messages_per_day", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column("escalation_after_failures", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # patient_communication_consents
    op.create_table(
        "patient_communication_consents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("consented", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("consent_source", sa.String(64), nullable=False),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_source", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_patient_communication_consents_patient_id", "patient_communication_consents", ["patient_id"])
    op.create_index("ix_patient_communication_consents_tenant_id", "patient_communication_consents", ["tenant_id"])

    # communication_channel_statuses
    op.create_table(
        "communication_channel_statuses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'HEALTHY'")),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_count_24h", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("success_count_24h", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_communication_channel_statuses_tenant_id", "communication_channel_statuses", ["tenant_id"])

    # ai_reply_decisions
    op.create_table(
        "ai_reply_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("communication_messages.id"), nullable=False),
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("communication_threads.id"), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("intent_detected", sa.String(64), nullable=False),
        sa.Column("reply_content", sa.Text(), nullable=True),
        sa.Column("escalation_reason", sa.String(255), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_reply_decisions_message_id", "ai_reply_decisions", ["message_id"])

    # human_takeover_states
    op.create_table(
        "human_takeover_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("communication_threads.id"), nullable=False, unique=True),
        sa.Column("assigned_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False, server_default=sa.text("'NORMAL'")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # fax_delivery_records
    op.create_table(
        "fax_delivery_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("telnyx_fax_id", sa.String(128), nullable=False, unique=True),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("to_number", sa.String(20), nullable=False),
        sa.Column("from_number", sa.String(20), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'QUEUED'")),
        sa.Column("media_url", sa.String(512), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_fax_delivery_records_tenant_id", "fax_delivery_records", ["tenant_id"])

    # address_verification_records
    op.create_table(
        "address_verification_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("input_address_line1", sa.String(255), nullable=False),
        sa.Column("input_city", sa.String(128), nullable=False),
        sa.Column("input_state", sa.String(2), nullable=False),
        sa.Column("input_zip", sa.String(10), nullable=False),
        sa.Column("verified_address_line1", sa.String(255), nullable=True),
        sa.Column("verified_city", sa.String(128), nullable=True),
        sa.Column("verified_state", sa.String(2), nullable=True),
        sa.Column("verified_zip", sa.String(10), nullable=True),
        sa.Column("deliverability", sa.String(32), nullable=False),
        sa.Column("lob_verification_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_address_verification_records_tenant_id", "address_verification_records", ["tenant_id"])

    # communication_audit_events
    op.create_table(
        "communication_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("communication_threads.id"), nullable=True),
        sa.Column("message_id", UUID(as_uuid=True), sa.ForeignKey("communication_messages.id"), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_type", sa.String(16), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("metadata_blob", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_communication_audit_events_tenant_id", "communication_audit_events", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("communication_audit_events")
    op.drop_table("address_verification_records")
    op.drop_table("fax_delivery_records")
    op.drop_table("human_takeover_states")
    op.drop_table("ai_reply_decisions")
    op.drop_table("communication_channel_statuses")
    op.drop_table("patient_communication_consents")
    op.drop_table("communication_policies")
    op.drop_table("communication_templates")
    op.drop_table("communication_delivery_events")
    op.drop_table("telecom_provisioning_runs")
    op.drop_table("communication_messages")
    op.drop_table("communication_threads")
    op.drop_table("agency_phone_numbers")
