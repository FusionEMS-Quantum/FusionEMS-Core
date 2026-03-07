"""Relationship History Models — longitudinal timelines, notes, warnings.

Timeline entries preserve source and timestamp. Internal notes are
permission-controlled. Warning flags are visible but auditable.
AI may summarize timelines, not rewrite them.
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
)
from core_app.models.tenant import TenantScopedMixin

# ── ENUMS ─────────────────────────────────────────────────────────────────────


class TimelineEventType(enum.StrEnum):
    PRIOR_TRIP = "PRIOR_TRIP"
    PRIOR_BALANCE = "PRIOR_BALANCE"
    PRIOR_FACILITY_CONTACT = "PRIOR_FACILITY_CONTACT"
    PRIOR_HANDOFF = "PRIOR_HANDOFF"
    PRIOR_DENIAL = "PRIOR_DENIAL"
    PRIOR_PAYMENT_PLAN = "PRIOR_PAYMENT_PLAN"
    PRIOR_COMMUNICATION = "PRIOR_COMMUNICATION"
    INTERNAL_NOTE = "INTERNAL_NOTE"
    WARNING_FLAG = "WARNING_FLAG"


class WarningFlagSeverity(enum.StrEnum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


# ── RELATIONSHIP TIMELINE EVENT ───────────────────────────────────────────────


class RelationshipTimelineEvent(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Longitudinal relationship event with provenance tracking."""

    __tablename__ = "relationship_timeline_events"
    __table_args__ = (
        Index(
            "ix_timeline_events_tenant_patient",
            "tenant_id", "patient_id",
        ),
        Index(
            "ix_timeline_events_tenant_facility",
            "tenant_id", "facility_id",
        ),
        Index(
            "ix_timeline_events_type",
            "tenant_id", "event_type",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=True
    )
    event_type: Mapped[TimelineEventType] = mapped_column(
        Enum(TimelineEventType, name="timeline_event_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # system, user, import, integration, ai_summary
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # referencing incident, claim, etc.
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )


# ── INTERNAL ACCOUNT NOTE ────────────────────────────────────────────────────


class InternalAccountNote(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Permission-controlled internal-only account notes."""

    __tablename__ = "internal_account_notes"
    __table_args__ = (
        Index(
            "ix_account_notes_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=True
    )
    note_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # billing, clinical, operational, general
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    is_sensitive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    visibility: Mapped[str] = mapped_column(
        String(32), nullable=False, default="internal"
    )  # internal, billing, admin_only


# ── PATIENT WARNING FLAG ──────────────────────────────────────────────────────


class PatientWarningFlag(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Visible, auditable warning flags on patient accounts."""

    __tablename__ = "patient_warning_flags"
    __table_args__ = (
        Index(
            "ix_patient_warnings_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    severity: Mapped[WarningFlagSeverity] = mapped_column(
        Enum(WarningFlagSeverity, name="warning_flag_severity"),
        nullable=False,
    )
    flag_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # frequent_utilizer, identity_risk, billing_risk, clinical_note
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


# ── FACILITY WARNING FLAG ─────────────────────────────────────────────────────


class FacilityWarningFlag(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Visible, auditable warning flags on facility relationships."""

    __tablename__ = "facility_warning_flags"
    __table_args__ = (
        Index(
            "ix_facility_warnings_tenant_facility",
            "tenant_id", "facility_id",
        ),
    )

    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    severity: Mapped[WarningFlagSeverity] = mapped_column(
        Enum(WarningFlagSeverity, name="warning_flag_severity"),
        nullable=False,
    )
    flag_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # high_friction, communication_gap, safety
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


# ── RELATIONSHIP SUMMARY SNAPSHOT ─────────────────────────────────────────────


class RelationshipSummarySnapshot(
    Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin,
):
    """Point-in-time AI or system-generated relationship summary."""

    __tablename__ = "relationship_summary_snapshots"
    __table_args__ = (
        Index(
            "ix_rel_snapshots_tenant_patient",
            "tenant_id", "patient_id",
        ),
    )

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=True
    )
    summary_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # ai_generated, system_rollup, manual
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # ai, system, user
    model_version: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_count: Mapped[int] = mapped_column(nullable=False, default=0)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
