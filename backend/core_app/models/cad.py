"""
CAD Domain Models
=================
Call intake, dispatch, unit management, and real-time tracking models.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base

# ── Enums ─────────────────────────────────────────────────────────────────────


class CADCallPriority(enum.StrEnum):
    ECHO = "ECHO"
    DELTA = "DELTA"
    CHARLIE = "CHARLIE"
    BRAVO = "BRAVO"
    ALPHA = "ALPHA"
    OMEGA = "OMEGA"


class CADCallState(enum.StrEnum):
    NEW = "NEW"
    INTAKE = "INTAKE"
    TRIAGED = "TRIAGED"
    DISPATCHED = "DISPATCHED"
    ENROUTE = "ENROUTE"
    ON_SCENE = "ON_SCENE"
    TRANSPORTING = "TRANSPORTING"
    AT_HOSPITAL = "AT_HOSPITAL"
    CLEARED = "CLEARED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class CADUnitState(enum.StrEnum):
    AVAILABLE = "AVAILABLE"
    ASSIGNED = "ASSIGNED"
    ENROUTE = "ENROUTE"
    ON_SCENE = "ON_SCENE"
    TRANSPORTING = "TRANSPORTING"
    AT_HOSPITAL = "AT_HOSPITAL"
    RETURNING = "RETURNING"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


# ── Core Models ───────────────────────────────────────────────────────────────


class CADCall(Base):
    """911/emergency call intake record."""

    __tablename__ = "cad_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    call_number: Mapped[str] = mapped_column(String(30), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default=CADCallState.NEW.value)
    priority: Mapped[str | None] = mapped_column(String(20))

    # Caller info
    caller_name: Mapped[str | None] = mapped_column(String(200))
    caller_phone: Mapped[str | None] = mapped_column(String(20))
    callback_number: Mapped[str | None] = mapped_column(String(20))

    # Location
    address: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    cross_street: Mapped[str | None] = mapped_column(String(200))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # Nature
    nature_of_call: Mapped[str | None] = mapped_column(String(200))
    chief_complaint: Mapped[str | None] = mapped_column(String(200))
    acuity_score: Mapped[int | None] = mapped_column(Integer)
    recommended_level: Mapped[str | None] = mapped_column(String(10))

    # Triage
    triage_notes: Mapped[str | None] = mapped_column(Text)
    intake_answers: Mapped[dict | None] = mapped_column(JSONB)

    # Timestamps
    call_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatch_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_enroute_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_on_scene_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transport_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    hospital_arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleared_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Linkage
    incident_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    epcr_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Relationships
    unit_assignments: Mapped[list[CADUnitAssignment]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )
    timeline_events: Mapped[list[CADTimelineEvent]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CADUnit(Base):
    """Dispatch unit (ambulance, fire engine, etc.)."""

    __tablename__ = "cad_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    unit_name: Mapped[str] = mapped_column(String(30), nullable=False)
    unit_type: Mapped[str] = mapped_column(String(30), nullable=False)
    service_level: Mapped[str | None] = mapped_column(String(10))
    state: Mapped[str] = mapped_column(String(30), default=CADUnitState.AVAILABLE.value)
    station: Mapped[str | None] = mapped_column(String(30))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    last_gps_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    readiness_score: Mapped[int] = mapped_column(Integer, default=100)
    crew_ids: Mapped[list | None] = mapped_column(JSONB)
    capabilities: Mapped[dict | None] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CADUnitAssignment(Base):
    """Unit assignment to a CAD call."""

    __tablename__ = "cad_unit_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cad_calls.id"), nullable=False
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    unit_name: Mapped[str] = mapped_column(String(30), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    enroute_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    on_scene_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    primary: Mapped[bool] = mapped_column(Boolean, default=False)

    call: Mapped[CADCall] = relationship(back_populates="unit_assignments")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CADTimelineEvent(Base):
    """Immutable timeline entry for a CAD call."""

    __tablename__ = "cad_timeline_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cad_calls.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    metadata_blob: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    call: Mapped[CADCall] = relationship(back_populates="timeline_events")


class CADUnitStatusEvent(Base):
    """Tracks unit state changes over time for analytics."""

    __tablename__ = "cad_unit_status_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    old_state: Mapped[str | None] = mapped_column(String(30))
    new_state: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(200))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
