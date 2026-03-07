"""Contact Preference Models — communication eligibility and opt-in/out.

Contact permissions must be explicit. Billing communications must respect
preference state. Preference changes must be logged.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from core_app.models.tenant import TenantScopedMixin

# ── ENUMS ─────────────────────────────────────────────────────────────────────


class ContactChannel(enum.StrEnum):
    SMS = "SMS"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    MAIL = "MAIL"
    FAX = "FAX"


class ContactPreferenceState(enum.StrEnum):
    SMS_ALLOWED = "SMS_ALLOWED"
    CALL_ALLOWED = "CALL_ALLOWED"
    EMAIL_ALLOWED = "EMAIL_ALLOWED"
    MAIL_REQUIRED = "MAIL_REQUIRED"
    CONTACT_RESTRICTED = "CONTACT_RESTRICTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class OptOutReason(enum.StrEnum):
    PATIENT_REQUEST = "PATIENT_REQUEST"
    LEGAL_REQUIREMENT = "LEGAL_REQUIREMENT"
    SYSTEM_POLICY = "SYSTEM_POLICY"
    DELIVERY_FAILURE = "DELIVERY_FAILURE"
    OTHER = "OTHER"


# ── CONTACT PREFERENCE ───────────────────────────────────────────────────────


class ContactPreference(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
    VersionMixin,
):
    """Explicit contact channel preferences for a patient or facility."""

    __tablename__ = "contact_preferences"
    __table_args__ = (
        Index(
            "ix_contact_prefs_tenant_patient",
            "tenant_id", "patient_id",
        ),
        Index(
            "ix_contact_prefs_tenant_facility",
            "tenant_id", "facility_id",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=True
    )
    sms_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    call_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    email_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    mail_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    contact_restricted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    preferred_channel: Mapped[ContactChannel | None] = mapped_column(
        Enum(ContactChannel, name="contact_channel"), nullable=True
    )
    preferred_time_start: Mapped[str | None] = mapped_column(
        String(8), nullable=True
    )  # HH:MM format
    preferred_time_end: Mapped[str | None] = mapped_column(
        String(8), nullable=True
    )
    facility_callback_preference: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── COMMUNICATION OPT-OUT EVENT ───────────────────────────────────────────────


class CommunicationOptOutEvent(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Immutable record of opt-in/opt-out changes."""

    __tablename__ = "communication_opt_out_events"
    __table_args__ = (
        Index(
            "ix_opt_out_events_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=True
    )
    channel: Mapped[ContactChannel] = mapped_column(
        Enum(ContactChannel, name="contact_channel"), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # opt_in, opt_out
    reason: Mapped[OptOutReason] = mapped_column(
        Enum(OptOutReason, name="opt_out_reason"), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── LANGUAGE PREFERENCE ───────────────────────────────────────────────────────


class LanguagePreference(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Patient language and interpreter preferences."""

    __tablename__ = "language_preferences"
    __table_args__ = (
        Index(
            "ix_lang_prefs_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    primary_language: Mapped[str] = mapped_column(
        String(32), nullable=False, default="en"
    )
    secondary_language: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    interpreter_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    interpreter_language: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── CONTACT POLICY AUDIT EVENT ────────────────────────────────────────────────


class ContactPolicyAuditEvent(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Immutable audit trail for contact preference/policy changes."""

    __tablename__ = "contact_policy_audit_events"
    __table_args__ = (
        Index(
            "ix_contact_policy_audit_tenant",
            "tenant_id",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # preference_updated, opt_out, opt_in, policy_override
    previous_state: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    new_state: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
