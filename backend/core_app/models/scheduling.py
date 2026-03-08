"""
Scheduling Domain Models
========================
Shift templates, instances, availability, swap requests,
credential tracking, fatigue compliance, and AI draft support.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base

# ── Enums ─────────────────────────────────────────────────────────────────────


class ShiftSwapState(enum.StrEnum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CANCELLED = "CANCELLED"


class CredentialState(enum.StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    PENDING_RENEWAL = "PENDING_RENEWAL"


# ── Core Models ───────────────────────────────────────────────────────────────


class ShiftTemplate(Base):
    """Reusable shift pattern definition (e.g., 24/48)."""

    __tablename__ = "scheduling_shift_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(30), nullable=False)
    shift_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    off_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    rotation_days: Mapped[int | None] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String(5), default="07:00")
    min_crew: Mapped[int] = mapped_column(Integer, default=2)
    required_roles: Mapped[list | None] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShiftInstance(Base):
    """Concrete shift assignment for a specific date."""

    __tablename__ = "scheduling_shift_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheduling_shift_templates.id")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    station: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str | None] = mapped_column(String(50))
    start_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_start_dt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_dt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overtime: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShiftSwapRequest(Base):
    """Peer-to-peer shift swap with approval workflow."""

    __tablename__ = "scheduling_swap_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    requester_shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheduling_shift_instances.id"), nullable=False
    )
    acceptor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    acceptor_shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheduling_shift_instances.id")
    )
    state: Mapped[str] = mapped_column(
        String(20), default=ShiftSwapState.REQUESTED.value
    )
    reason: Mapped[str | None] = mapped_column(Text)
    approver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    denied_reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AvailabilityBlock(Base):
    """Crew availability or unavailability window."""

    __tablename__ = "scheduling_availability"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    start_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TimeOffRequest(Base):
    """Time-off request with approval."""

    __tablename__ = "scheduling_time_off"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    category: Mapped[str] = mapped_column(String(30), default="PTO")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    approver_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CrewCredential(Base):
    """Credential/certification tracking for crew members."""

    __tablename__ = "scheduling_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    credential_type: Mapped[str] = mapped_column(String(50), nullable=False)
    credential_number: Mapped[str | None] = mapped_column(String(100))
    issuing_authority: Mapped[str | None] = mapped_column(String(200))
    issued_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(30), default=CredentialState.ACTIVE.value)
    document_s3_key: Mapped[str | None] = mapped_column(String(500))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FatigueAssessment(Base):
    """NFPA-aligned fatigue tracking for crew scheduling."""

    __tablename__ = "scheduling_fatigue_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    kss_score: Mapped[int | None] = mapped_column(Integer)
    hours_on_duty: Mapped[float | None] = mapped_column(Float)
    hours_since_last_sleep: Mapped[float | None] = mapped_column(Float)
    calls_this_shift: Mapped[int] = mapped_column(Integer, default=0)
    fatigue_risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    assessment_notes: Mapped[str | None] = mapped_column(Text)
    fit_for_duty: Mapped[bool] = mapped_column(Boolean, default=True)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CoverageRule(Base):
    """Minimum staffing and coverage requirements per station/unit."""

    __tablename__ = "scheduling_coverage_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    station: Mapped[str | None] = mapped_column(String(30))
    unit_type: Mapped[str | None] = mapped_column(String(30))
    min_personnel: Mapped[int] = mapped_column(Integer, default=2)
    required_roles: Mapped[list | None] = mapped_column(JSONB)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
