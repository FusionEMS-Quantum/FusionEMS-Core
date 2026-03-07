"""Facility Network Models — hospital/SNF/LTC profiles, contacts, relationships.

Boundary: Facilities are separate from agency tenant records.
A facility may be an external partner without being a platform tenant.
No silent overwrites of contacts or relationship notes.
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
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from core_app.models.tenant import TenantScopedMixin

# ── ENUMS ─────────────────────────────────────────────────────────────────────


class FacilityType(enum.StrEnum):
    HOSPITAL = "HOSPITAL"
    SNF = "SNF"
    LTC = "LTC"
    REHAB = "REHAB"
    DIALYSIS = "DIALYSIS"
    PSYCHIATRIC = "PSYCHIATRIC"
    URGENT_CARE = "URGENT_CARE"
    PHYSICIANS_OFFICE = "PHYSICIANS_OFFICE"
    HOME_HEALTH = "HOME_HEALTH"
    OTHER = "OTHER"


class FacilityRelationshipState(enum.StrEnum):
    ACTIVE = "ACTIVE"
    LIMITED_RELATIONSHIP = "LIMITED_RELATIONSHIP"
    HIGH_FRICTION = "HIGH_FRICTION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INACTIVE = "INACTIVE"


class FacilityContactRole(enum.StrEnum):
    INTAKE_COORDINATOR = "INTAKE_COORDINATOR"
    NURSE = "NURSE"
    SOCIAL_WORKER = "SOCIAL_WORKER"
    CASE_MANAGER = "CASE_MANAGER"
    CHARGE_NURSE = "CHARGE_NURSE"
    ADMINISTRATOR = "ADMINISTRATOR"
    BILLING_CONTACT = "BILLING_CONTACT"
    DISPATCH_LIAISON = "DISPATCH_LIAISON"
    OTHER = "OTHER"


class FrictionCategory(enum.StrEnum):
    WAIT_TIMES = "WAIT_TIMES"
    COMMUNICATION = "COMMUNICATION"
    DOCUMENTATION = "DOCUMENTATION"
    BILLING_DISPUTES = "BILLING_DISPUTES"
    SAFETY_CONCERN = "SAFETY_CONCERN"
    STAFF_CONFLICT = "STAFF_CONFLICT"
    OTHER = "OTHER"


# ── FACILITY ──────────────────────────────────────────────────────────────────


class Facility(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
    SoftDeleteMixin, VersionMixin,
):
    """External facility profile (hospital, SNF, LTC, etc.)."""

    __tablename__ = "facilities"
    __table_args__ = (
        Index("ix_facilities_tenant_type", "tenant_id", "facility_type"),
        Index("ix_facilities_tenant_state", "tenant_id", "relationship_state"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_type: Mapped[FacilityType] = mapped_column(
        Enum(FacilityType, name="facility_type"), nullable=False
    )
    npi: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    fax: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relationship_state: Mapped[FacilityRelationshipState] = mapped_column(
        Enum(FacilityRelationshipState, name="facility_relationship_state"),
        nullable=False,
        default=FacilityRelationshipState.ACTIVE,
    )
    destination_preference_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    service_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    facility_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


# ── FACILITY CONTACT ─────────────────────────────────────────────────────────


class FacilityContact(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Named contact at a facility (nurse, case manager, intake, etc.)."""

    __tablename__ = "facility_contacts"
    __table_args__ = (
        Index(
            "ix_facility_contacts_tenant_facility",
            "tenant_id", "facility_id",
        ),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[FacilityContactRole] = mapped_column(
        Enum(FacilityContactRole, name="facility_contact_role"),
        nullable=False,
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_contact_method: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # phone, email, fax
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


# ── FACILITY RELATIONSHIP NOTE ────────────────────────────────────────────────


class FacilityRelationshipNote(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Operational and billing relationship notes for a facility."""

    __tablename__ = "facility_relationship_notes"
    __table_args__ = (
        Index(
            "ix_facility_rel_notes_tenant_facility",
            "tenant_id", "facility_id",
        ),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    note_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # operational, billing, handoff, general
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    is_internal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


# ── FACILITY SERVICE PROFILE ─────────────────────────────────────────────────


class FacilityServiceProfile(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Service lines and capabilities for a facility."""

    __tablename__ = "facility_service_profiles"
    __table_args__ = (
        Index(
            "ix_facility_svc_tenant_facility",
            "tenant_id", "facility_id",
        ),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    service_line: Mapped[str] = mapped_column(
        String(128), nullable=False
    )  # ER, ICU, Med-Surg, Stroke Center, etc.
    accepts_ems_transport: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    average_turnaround_minutes: Mapped[int | None] = mapped_column(
        nullable=True
    )
    capability_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


# ── FACILITY FRICTION FLAG ────────────────────────────────────────────────────


class FacilityFrictionFlag(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Tracks friction/issues at facilities for operational awareness."""

    __tablename__ = "facility_friction_flags"
    __table_args__ = (
        Index(
            "ix_facility_friction_tenant_facility",
            "tenant_id", "facility_id",
        ),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    category: Mapped[FrictionCategory] = mapped_column(
        Enum(FrictionCategory, name="friction_category"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── FACILITY AUDIT EVENT ─────────────────────────────────────────────────────


class FacilityAuditEvent(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Immutable audit trail for facility data changes."""

    __tablename__ = "facility_audit_events"
    __table_args__ = (
        Index(
            "ix_facility_audit_tenant_facility",
            "tenant_id", "facility_id",
        ),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # created, updated, contact_added, friction_flagged, etc.
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
