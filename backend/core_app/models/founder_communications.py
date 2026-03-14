"""
Founder Communications Models
==============================
Founder-only persistent records for all communication channels:
  - Outbound calls / call recordings / transcripts  (Telnyx)
  - SMS threads                                      (Telnyx)
  - Fax records                                      (Telnyx)
  - Print / mail jobs                                (LOB)
  - Platform alert records
  - Audio alert configuration
  - Reusable message templates
  - BAA (Business Associate Agreement) templates
  - Wisconsin-specific document templates

Scope: Founder-only. NOT tenant-scoped. All rows are global to the platform.
Auditable: every mutation must produce a structured log entry.
"""
from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# ── Enums ──────────────────────────────────────────────────────────────────────

class CallDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(StrEnum):
    INITIATED = "initiated"
    RINGING = "ringing"
    ANSWERED = "answered"
    COMPLETED = "completed"
    FAILED = "failed"
    NO_ANSWER = "no_answer"
    BUSY = "busy"


class FaxStatus(StrEnum):
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RECEIVED = "received"


class PrintMailStatus(StrEnum):
    QUEUED = "queued"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    RETURNED = "returned"
    FAILED = "failed"


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    VOICE = "voice"
    AUDIT_LOG = "audit_log"


class CommsChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    FAX = "fax"
    VOICE = "voice"
    PRINT_MAIL = "print_mail"


# ── Models ────────────────────────────────────────────────────────────────────

class FounderCallRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Record of every call initiated or received by the founder's phone number.
    Links to Telnyx call_control_id for live call management.
    """
    __tablename__ = "founder_call_records"

    telnyx_call_control_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    telnyx_call_leg_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default=CallDirection.OUTBOUND)
    from_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_number: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=CallStatus.INITIATED)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class FounderSMSThread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Append-only SMS thread for founder-to-contact conversations.
    messages: list of {role: 'founder'|'contact', body: str, ts: ISO, telnyx_id: str|null}
    """
    __tablename__ = "founder_sms_threads"

    to_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    messages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    last_message_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FounderFaxRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Outbound or inbound fax record.
    s3_key holds the PDF stored post-receive/send.
    """
    __tablename__ = "founder_fax_records"

    telnyx_fax_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="outbound")
    from_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_number: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=FaxStatus.QUEUED)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class FounderPrintMailRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    LOB print-and-mail letter record. Tracks the full lifecycle from queue → delivery.
    recipient_address: {name, address_line1, address_line2, city, state, zip}
    """
    __tablename__ = "founder_print_mail_records"

    lob_letter_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=PrintMailStatus.QUEUED)
    template_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_variables: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recipient_address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    subject_line: Mapped[str | None] = mapped_column(String(256), nullable=True)
    expected_delivery_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tracking_events: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class FounderAlertRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Platform-level alert dispatched to the founder via one or more channels.
    Immutable once created; acknowledged_at is set on read-receipt.
    """
    __tablename__ = "founder_alert_records"

    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default=AlertSeverity.INFO)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    acknowledged_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    alert_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)


class FounderAudioAlertConfig(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Configuration for audio alerts — maps alert_type to an audio file (S3 URL or public CDN).
    Used for in-browser audio playback and Telnyx call_speak fallback.
    """
    __tablename__ = "founder_audio_alert_configs"

    alert_type: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tts_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FounderCommunicationTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Reusable message template for any channel.
    body_template uses {{variable_name}} substitution syntax.
    variables: list of {name: str, required: bool, description: str}
    """
    __tablename__ = "founder_communication_templates"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class BAATemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Business Associate Agreement template.
    body_html uses {{variable_name}} substitution.
    effective_date: ISO date string when this revision became effective.
    """
    __tablename__ = "baa_templates"

    template_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(48), nullable=False, default="v1.0")
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    effective_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class WisconsinDocTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Wisconsin-specific legal / compliance document template.
    doc_type: e.g. 'retention_notice', 'legal_hold_letter', 'audit_disclosure', 'tax_consent'
    """
    __tablename__ = "wisconsin_doc_templates"

    doc_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(48), nullable=False, default="v1.0")
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    effective_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    wi_statute_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
