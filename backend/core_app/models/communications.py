# pylint: disable=unsubscriptable-object
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CommunicationThreadState(StrEnum):
    """
    BILLING COMMUNICATIONS LIFECYCLE STATE MACHINE
    Defined in FINAL_BUILD_STATEMENT.md Section 5E.
    """
    THREAD_CREATED = "THREAD_CREATED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    AI_REVIEWED = "AI_REVIEWED"
    AI_REPLIED = "AI_REPLIED"
    HUMAN_TAKEOVER = "HUMAN_TAKEOVER"
    MESSAGE_DELIVERED = "MESSAGE_DELIVERED"
    MESSAGE_FAILED = "MESSAGE_FAILED"
    MAIL_FALLBACK_PENDING = "MAIL_FALLBACK_PENDING"
    MAIL_SENT = "MAIL_SENT"
    CLOSED = "CLOSED"


class AgencyPhoneNumber(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Telnyx Phone Number assigned to an agency for Billing Comms.
    Strictly billing-only.
    """
    __tablename__ = "agency_phone_numbers"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False) # e.g. +19195551234
    telnyx_phone_number_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # Configuration
    voice_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    sms_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    fax_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False) # ACTIVE, RELEASED, PENDING


class CommunicationThread(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Siloed conversation thread (Billing Support, Patient Payment).
    Auditable and viewable in dashboard.
    """
    __tablename__ = "communication_threads"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)

    channel: Mapped[str] = mapped_column(String(16), default="SMS", nullable=False) # SMS, EMAIL, VOICE
    topic: Mapped[str] = mapped_column(String(32), default="BILLING_GENERAL", nullable=False) # PATIENT_BALANCE, BILLING_SUPPORT

    status: Mapped[CommunicationThreadState] = mapped_column(String(32), default=CommunicationThreadState.THREAD_CREATED, nullable=False)
    latest_message_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)


class CommunicationMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual message in a thread.
    """
    __tablename__ = "communication_messages"

    thread_id: Mapped[UUID] = mapped_column(ForeignKey("communication_threads.id"), nullable=False, index=True)

    direction: Mapped[str] = mapped_column(String(16), nullable=False) # INBOUND, OUTBOUND
    content: Mapped[str] = mapped_column(Text, nullable=False)

    sender_type: Mapped[str] = mapped_column(String(16), default="SYSTEM", nullable=False) # SYSTEM, AI, HUMAN, PATIENT
    ai_generated: Mapped[bool] = mapped_column(default=False, nullable=False)

    telnyx_message_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="SENT", nullable=False) # QUEUED, SENT, DELIVERED, FAILED


class MailFulfillmentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Physical mail sent via Lob (e.g. Statements, Notices).
    """
    __tablename__ = "mail_fulfillment_records"

    claim_id: Mapped[UUID | None] = mapped_column(ForeignKey("claims.id"), nullable=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)

    lob_letter_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False) # e.g. "STATEMENT_V1"

    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False) # CREATED, MAILED, IN_TRANSIT, DELIVERED, RETURNED
    expected_delivery_date: Mapped[datetime | None] = mapped_column(nullable=True)


class TelecomProvisioningRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks provisioning of phone numbers via Telnyx for an agency.
    Each run represents an attempt to provision or release numbers.
    """
    __tablename__ = "telecom_provisioning_runs"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    action: Mapped[str] = mapped_column(String(32), nullable=False)  # PROVISION, RELEASE, UPDATE
    requested_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provisioned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    telnyx_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class CommunicationDeliveryEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks delivery status updates for individual messages.
    Sourced from Telnyx/Lob webhooks. Provides delivery audit trail.
    """
    __tablename__ = "communication_delivery_events"

    message_id: Mapped[UUID] = mapped_column(ForeignKey("communication_messages.id"), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # QUEUED, SENT, DELIVERED, FAILED, BOUNCED
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # TELNYX, LOB, SES
    provider_event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)


class CommunicationTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Reusable message templates for billing communications.
    Supports variable substitution (patient name, balance, link).
    """
    __tablename__ = "communication_templates"

    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)  # NULL = platform-wide

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # SMS, EMAIL, MAIL, FAX
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # BALANCE_REMINDER, PAYMENT_RECEIPT, STATEMENT, etc.
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)  # For email/mail
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)  # ["patient_name", "balance", "payment_link"]
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class CommunicationPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Per-agency communication policy. Controls which channels are allowed,
    timing restrictions, and escalation rules.
    """
    __tablename__ = "communication_policies"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), unique=True, nullable=False)

    sms_allowed: Mapped[bool] = mapped_column(default=True, nullable=False)
    email_allowed: Mapped[bool] = mapped_column(default=True, nullable=False)
    voice_allowed: Mapped[bool] = mapped_column(default=False, nullable=False)
    fax_allowed: Mapped[bool] = mapped_column(default=False, nullable=False)
    mail_allowed: Mapped[bool] = mapped_column(default=True, nullable=False)
    ai_auto_reply_allowed: Mapped[bool] = mapped_column(default=True, nullable=False)
    quiet_hours_start: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Hour 0-23
    quiet_hours_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_messages_per_day: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    escalation_after_failures: Mapped[int] = mapped_column(Integer, default=3, nullable=False)


class PatientCommunicationConsent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    TCPA/opt-in compliance record per patient per channel.
    Required for SMS/voice. Tracks consent source and revocation.
    """
    __tablename__ = "patient_communication_consents"

    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # SMS, EMAIL, VOICE, MAIL
    consented: Mapped[bool] = mapped_column(default=False, nullable=False)
    consent_source: Mapped[str] = mapped_column(String(64), nullable=False)  # INTAKE_FORM, WEB_PORTAL, SMS_KEYWORD, MANUAL
    consent_given_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    revocation_source: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SMS_STOP, WEB_PORTAL, MANUAL, PHONE_REQUEST


class CommunicationChannelStatus(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks the operational health of each communication channel.
    Updated by webhook health checks and delivery analytics.
    """
    __tablename__ = "communication_channel_statuses"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # SMS, EMAIL, FAX, VOICE, MAIL
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # TELNYX, SES, LOB
    status: Mapped[str] = mapped_column(String(32), default="HEALTHY", nullable=False)  # HEALTHY, DEGRADED, DOWN, UNKNOWN
    last_success_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failure_count_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count_24h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(nullable=False)


class AIReplyDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks AI's decision to auto-reply or escalate incoming messages.
    Provides audit trail for all AI-generated responses.
    """
    __tablename__ = "ai_reply_decisions"

    message_id: Mapped[UUID] = mapped_column(ForeignKey("communication_messages.id"), nullable=False, index=True)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("communication_threads.id"), nullable=False)

    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # AUTO_REPLY, ESCALATE, SUPPRESS, DEFER
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    intent_detected: Mapped[str] = mapped_column(String(64), nullable=False)  # PAYMENT_QUESTION, DISPUTE, OPT_OUT, GENERAL
    reply_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)


class HumanTakeoverState(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks human escalation state for communication threads.
    When AI cannot handle a message, a human agent takes over.
    """
    __tablename__ = "human_takeover_states"

    thread_id: Mapped[UUID] = mapped_column(ForeignKey("communication_threads.id"), unique=True, nullable=False)

    assigned_user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="NORMAL", nullable=False)  # LOW, NORMAL, HIGH, URGENT
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)  # PENDING, ASSIGNED, IN_PROGRESS, RESOLVED
    escalated_at: Mapped[datetime] = mapped_column(nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)


class FaxDeliveryRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks fax transmissions via Telnyx fax API.
    Used for payer correspondence, prior auth, and appeal documents.
    """
    __tablename__ = "fax_delivery_records"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    telnyx_fax_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # OUTBOUND, INBOUND
    to_number: Mapped[str] = mapped_column(String(20), nullable=False)
    from_number: Mapped[str] = mapped_column(String(20), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False)  # QUEUED, SENDING, DELIVERED, FAILED
    media_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AddressVerificationRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks address verification results from Lob for mail fulfillment.
    Ensures USPS-deliverable addresses before printing.
    """
    __tablename__ = "address_verification_records"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("patients.id"), nullable=True)

    input_address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    input_city: Mapped[str] = mapped_column(String(128), nullable=False)
    input_state: Mapped[str] = mapped_column(String(2), nullable=False)
    input_zip: Mapped[str] = mapped_column(String(10), nullable=False)
    verified_address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verified_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verified_state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    verified_zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    deliverability: Mapped[str] = mapped_column(String(32), nullable=False)  # DELIVERABLE, UNDELIVERABLE, NO_MATCH
    lob_verification_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class CommunicationAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Comprehensive audit trail for all communication actions.
    Covers sends, deliveries, opt-outs, escalations, policy enforcement.
    """
    __tablename__ = "communication_audit_events"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    thread_id: Mapped[UUID | None] = mapped_column(ForeignKey("communication_threads.id"), nullable=True)
    message_id: Mapped[UUID | None] = mapped_column(ForeignKey("communication_messages.id"), nullable=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # MESSAGE_SENT, DELIVERY_CONFIRMED, OPT_OUT, ESCALATION, POLICY_BLOCK
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)  # SYSTEM, AI, HUMAN, PATIENT
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_blob: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
