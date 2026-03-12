"""Add founder communications tables

Revision ID: 20260313_0045
Revises: 20260310_0044
Create Date: 2026-03-13
"""
from __future__ import annotations

# pylint: disable=no-name-in-module

from alembic import op  # pyright: ignore[reportAttributeAccessIssue]
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260313_0045"
down_revision = "20260310_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # founder_call_records
    op.create_table(
        "founder_call_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("telnyx_call_control_id", sa.String(128), nullable=True),
        sa.Column("telnyx_call_leg_id", sa.String(128), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False, server_default="outbound"),
        sa.Column("from_number", sa.String(30), nullable=True),
        sa.Column("to_number", sa.String(30), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="initiated"),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("recording_url", sa.Text, nullable=True),
        sa.Column("recording_s3_key", sa.Text, nullable=True),
        sa.Column("transcript", sa.Text, nullable=True),
        sa.Column("ai_summary", sa.Text, nullable=True),
        sa.Column("call_metadata", JSONB, nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_call_records_telnyx_call_control_id", "founder_call_records", ["telnyx_call_control_id"])
    op.create_index("ix_founder_call_records_correlation_id", "founder_call_records", ["correlation_id"])

    # founder_sms_threads
    op.create_table(
        "founder_sms_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("to_number", sa.String(30), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("messages", JSONB, nullable=False, server_default="[]"),
        sa.Column("last_message_at", sa.String(32), nullable=True),
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_sms_threads_to_number", "founder_sms_threads", ["to_number"])

    # founder_fax_records
    op.create_table(
        "founder_fax_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("telnyx_fax_id", sa.String(128), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False, server_default="outbound"),
        sa.Column("from_number", sa.String(30), nullable=True),
        sa.Column("to_number", sa.String(30), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="queued"),
        sa.Column("page_count", sa.Integer, nullable=True),
        sa.Column("subject", sa.String(256), nullable=True),
        sa.Column("s3_key", sa.Text, nullable=True),
        sa.Column("media_url", sa.Text, nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_fax_records_telnyx_fax_id", "founder_fax_records", ["telnyx_fax_id"])
    op.create_index("ix_founder_fax_records_correlation_id", "founder_fax_records", ["correlation_id"])

    # founder_print_mail_records
    op.create_table(
        "founder_print_mail_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lob_letter_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("template_id", sa.String(128), nullable=True),
        sa.Column("template_variables", JSONB, nullable=True),
        sa.Column("recipient_address", JSONB, nullable=True),
        sa.Column("subject_line", sa.String(256), nullable=True),
        sa.Column("expected_delivery_date", sa.String(32), nullable=True),
        sa.Column("tracking_events", JSONB, nullable=True, server_default="[]"),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_print_mail_records_lob_letter_id", "founder_print_mail_records", ["lob_letter_id"])

    # founder_alert_records
    op.create_table(
        "founder_alert_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("channel", sa.String(24), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("subject", sa.String(256), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("source_system", sa.String(64), nullable=True),
        sa.Column("delivery_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("acknowledged_at", sa.String(32), nullable=True),
        sa.Column("alert_metadata", JSONB, nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_alert_records_correlation_id", "founder_alert_records", ["correlation_id"])
    op.create_index("ix_founder_alert_records_severity", "founder_alert_records", ["severity"])

    # founder_audio_alert_configs
    op.create_table(
        "founder_audio_alert_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_type", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("audio_url", sa.Text, nullable=True),
        sa.Column("tts_script", sa.Text, nullable=True),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # founder_communication_templates
    op.create_table(
        "founder_communication_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("channel", sa.String(24), nullable=False),
        sa.Column("subject", sa.String(256), nullable=True),
        sa.Column("body_template", sa.Text, nullable=False),
        sa.Column("variables", JSONB, nullable=True, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_founder_communication_templates_channel", "founder_communication_templates", ["channel"])

    # baa_templates
    op.create_table(
        "baa_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_name", sa.String(128), nullable=False),
        sa.Column("version_tag", sa.String(48), nullable=False, server_default="v1.0"),
        sa.Column("body_html", sa.Text, nullable=False),
        sa.Column("variables", JSONB, nullable=True, server_default="[]"),
        sa.Column("effective_date", sa.String(32), nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # wisconsin_doc_templates
    op.create_table(
        "wisconsin_doc_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("version_tag", sa.String(48), nullable=False, server_default="v1.0"),
        sa.Column("body_html", sa.Text, nullable=False),
        sa.Column("variables", JSONB, nullable=True, server_default="[]"),
        sa.Column("effective_date", sa.String(32), nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("wi_statute_reference", sa.String(128), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_wisconsin_doc_templates_doc_type", "wisconsin_doc_templates", ["doc_type"])


def downgrade() -> None:
    op.drop_table("wisconsin_doc_templates")
    op.drop_table("baa_templates")
    op.drop_table("founder_communication_templates")
    op.drop_table("founder_audio_alert_configs")
    op.drop_table("founder_alert_records")
    op.drop_table("founder_print_mail_records")
    op.drop_table("founder_fax_records")
    op.drop_table("founder_sms_threads")
    op.drop_table("founder_call_records")
