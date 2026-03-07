"""Responsible Party Models — guarantor, subscriber, financial responsibility.

Boundary: Patient identity is separate from billing responsibility.
A patient may not be the financially responsible party.
All responsibility assignments require explicit review.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
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


class ResponsibilityState(enum.StrEnum):
    UNKNOWN = "UNKNOWN"
    PATIENT_SELF = "PATIENT_SELF"
    GUARANTOR_IDENTIFIED = "GUARANTOR_IDENTIFIED"
    SUBSCRIBER_IDENTIFIED = "SUBSCRIBER_IDENTIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    DISPUTED = "DISPUTED"


class RelationshipToPatient(enum.StrEnum):
    SELF = "SELF"
    SPOUSE = "SPOUSE"
    PARENT = "PARENT"
    CHILD = "CHILD"
    GUARDIAN = "GUARDIAN"
    OTHER = "OTHER"


# ── RESPONSIBLE PARTY ─────────────────────────────────────────────────────────


class ResponsibleParty(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
    VersionMixin,
):
    """A person who may be financially responsible for a patient's account."""

    __tablename__ = "responsible_parties"
    __table_args__ = (
        Index("ix_responsible_parties_tenant", "tenant_id"),
    )

    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    address_line_2: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── PATIENT ↔ RESPONSIBLE PARTY LINK ─────────────────────────────────────────


class PatientResponsiblePartyLink(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Explicit link between a patient and a responsible party."""

    __tablename__ = "patient_responsible_party_links"
    __table_args__ = (
        Index(
            "ix_prp_links_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    responsible_party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("responsible_parties.id"),
        nullable=False,
    )
    relationship_to_patient: Mapped[RelationshipToPatient] = mapped_column(
        Enum(RelationshipToPatient, name="relationship_to_patient"),
        nullable=False,
    )
    responsibility_state: Mapped[ResponsibilityState] = mapped_column(
        Enum(ResponsibilityState, name="responsibility_state"),
        nullable=False,
        default=ResponsibilityState.UNKNOWN,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── INSURANCE SUBSCRIBER PROFILE ──────────────────────────────────────────────


class InsuranceSubscriberProfile(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
    VersionMixin,
):
    """The person who holds the insurance policy (may differ from patient)."""

    __tablename__ = "insurance_subscriber_profiles"
    __table_args__ = (
        Index(
            "ix_subscriber_profiles_tenant",
            "tenant_id",
        ),
    )

    responsible_party_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("responsible_parties.id"),
        nullable=False,
    )
    insurance_carrier: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    policy_number: Mapped[str] = mapped_column(String(64), nullable=False)
    group_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    member_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subscriber_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subscriber_dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    relationship_to_subscriber: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # self, spouse, child, other
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


# ── RESPONSIBILITY AUDIT EVENT ────────────────────────────────────────────────


class ResponsibilityAuditEvent(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Immutable audit record for all financial responsibility changes."""

    __tablename__ = "responsibility_audit_events"
    __table_args__ = (
        Index(
            "ix_resp_audit_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    responsible_party_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # linked, unlinked, state_changed, disputed, resolved
    previous_state: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    new_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
