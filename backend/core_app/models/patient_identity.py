"""Patient Identity Models — canonical identity, alias, duplicate detection, merge workflow.

State Machine: PROFILE_CREATED → VERIFIED | DUPLICATE_CANDIDATE → MERGE_REVIEW_REQUIRED → MERGED
All identity mutations are auditable. No silent merges permitted.
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from core_app.models.tenant import TenantScopedMixin

# ── ENUMS ─────────────────────────────────────────────────────────────────────


class PatientIdentityState(enum.StrEnum):
    PROFILE_CREATED = "PROFILE_CREATED"
    PROFILE_INCOMPLETE = "PROFILE_INCOMPLETE"
    DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"
    VERIFIED = "VERIFIED"
    MERGE_REVIEW_REQUIRED = "MERGE_REVIEW_REQUIRED"
    MERGED = "MERGED"
    CORRECTION_PENDING = "CORRECTION_PENDING"
    ARCHIVED = "ARCHIVED"


class IdentifierSource(enum.StrEnum):
    MRN = "MRN"
    SSN_LAST4 = "SSN_LAST4"
    DRIVERS_LICENSE = "DRIVERS_LICENSE"
    MEDICAID_ID = "MEDICAID_ID"
    MEDICARE_ID = "MEDICARE_ID"
    INSURANCE_MEMBER_ID = "INSURANCE_MEMBER_ID"
    FACILITY_ASSIGNED = "FACILITY_ASSIGNED"
    EXTERNAL_SYSTEM = "EXTERNAL_SYSTEM"
    OTHER = "OTHER"


class MergeRequestStatus(enum.StrEnum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"
    ROLLED_BACK = "ROLLED_BACK"


class DuplicateResolution(enum.StrEnum):
    UNRESOLVED = "UNRESOLVED"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
    NOT_DUPLICATE = "NOT_DUPLICATE"
    MERGED = "MERGED"


class RelationshipFlagSeverity(enum.StrEnum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


# ── PATIENT ALIAS ─────────────────────────────────────────────────────────────


class PatientAlias(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin
):
    """Alternate names for a patient (maiden, preferred, legal change)."""

    __tablename__ = "patient_aliases"
    __table_args__ = (
        Index("ix_patient_aliases_tenant_patient", "tenant_id", "patient_id"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    alias_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # maiden, preferred, legal, nickname
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── PATIENT IDENTIFIER ────────────────────────────────────────────────────────


class PatientIdentifier(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin
):
    """External identifiers with provenance (MRN, Medicaid, insurance ID)."""

    __tablename__ = "patient_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "source", "identifier_value",
            name="uq_patient_identifier_source_value",
        ),
        Index(
            "ix_patient_identifiers_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    source: Mapped[IdentifierSource] = mapped_column(
        Enum(IdentifierSource, name="identifier_source"), nullable=False
    )
    identifier_value: Mapped[str] = mapped_column(String(128), nullable=False)
    issuing_authority: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    provenance: Mapped[str] = mapped_column(
        String(64), nullable=False, default="manual"
    )  # manual, import, integration
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )


# ── DUPLICATE CANDIDATE ──────────────────────────────────────────────────────


class PatientDuplicateCandidate(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin
):
    """Suggested duplicate pair with confidence score. Never auto-resolved."""

    __tablename__ = "patient_duplicate_candidates"
    __table_args__ = (
        Index(
            "ix_dup_candidates_tenant",
            "tenant_id", "resolution",
        ),
    )

    patient_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    patient_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    confidence_score: Mapped[float] = mapped_column(nullable=False)
    match_criteria: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # what fields matched
    resolution: Mapped[DuplicateResolution] = mapped_column(
        Enum(DuplicateResolution, name="duplicate_resolution"),
        nullable=False,
        default=DuplicateResolution.UNRESOLVED,
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# ── MERGE REQUEST ─────────────────────────────────────────────────────────────


class PatientMergeRequest(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin
):
    """Explicit merge request requiring human review and approval."""

    __tablename__ = "patient_merge_requests"
    __table_args__ = (
        Index("ix_merge_requests_tenant_status", "tenant_id", "status"),
    )

    source_patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    target_patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    status: Mapped[MergeRequestStatus] = mapped_column(
        Enum(MergeRequestStatus, name="merge_request_status"),
        nullable=False,
        default=MergeRequestStatus.PENDING_REVIEW,
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    merge_reason: Mapped[str] = mapped_column(Text, nullable=False)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_resolution_map: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )  # which fields kept from which patient


# ── MERGE AUDIT EVENT ─────────────────────────────────────────────────────────


class PatientMergeAuditEvent(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin
):
    """Immutable audit trail for every merge lifecycle event."""

    __tablename__ = "patient_merge_audit_events"
    __table_args__ = (
        Index(
            "ix_merge_audit_tenant_request",
            "tenant_id", "merge_request_id",
        ),
    )

    merge_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patient_merge_requests.id"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # requested, approved, rejected, executed, rolled_back
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )


# ── RELATIONSHIP FLAG ─────────────────────────────────────────────────────────


class PatientRelationshipFlag(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin
):
    """Visible, auditable flags on patient relationships (warnings, notes)."""

    __tablename__ = "patient_relationship_flags"
    __table_args__ = (
        Index(
            "ix_patient_rel_flags_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    flag_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # identity_conflict, billing_dispute, frequent_utilizer
    severity: Mapped[RelationshipFlagSeverity] = mapped_column(
        Enum(RelationshipFlagSeverity, name="relationship_flag_severity"),
        nullable=False,
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
