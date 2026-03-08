"""
Fire/NERIS Domain Models
========================
NERIS 5.0 compliant models for fire incident reporting, preplans,
hydrants, inspections, and export tracking.
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


class NERISIncidentType(enum.StrEnum):
    FIRE = "FIRE"
    OVERPRESSURE = "OVERPRESSURE"
    EMS = "EMS"
    HAZMAT = "HAZMAT"
    SERVICE_CALL = "SERVICE_CALL"
    GOOD_INTENT = "GOOD_INTENT"
    FALSE_ALARM = "FALSE_ALARM"
    SEVERE_WEATHER = "SEVERE_WEATHER"
    SPECIAL = "SPECIAL"


class NERISExportState(enum.StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class FireInspectionStatus(enum.StrEnum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CORRECTIVE_ACTION = "CORRECTIVE_ACTION"
    CLOSED = "CLOSED"


# ── Core Models ───────────────────────────────────────────────────────────────


class FireIncident(Base):
    """NERIS Basic Module (Section A) plus fire-specific fields."""

    __tablename__ = "fire_neris_incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    incident_number: Mapped[str] = mapped_column(String(30), nullable=False)
    incident_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(30), nullable=False)
    neris_incident_type_code: Mapped[str | None] = mapped_column(String(10))

    # NERIS Section A — Basic
    alarm_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrival_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    controlled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_unit_cleared_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shift: Mapped[str | None] = mapped_column(String(10))
    district: Mapped[str | None] = mapped_column(String(20))
    station: Mapped[str | None] = mapped_column(String(20))
    exposure_number: Mapped[int] = mapped_column(Integer, default=0)

    # Location
    street_address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(2))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    # NERIS Section B — Property
    property_use_code: Mapped[str | None] = mapped_column(String(10))
    mixed_use: Mapped[str | None] = mapped_column(String(10))
    census_tract: Mapped[str | None] = mapped_column(String(20))

    # NERIS Section C — Fire origin/cause
    area_of_origin_code: Mapped[str | None] = mapped_column(String(10))
    heat_source_code: Mapped[str | None] = mapped_column(String(10))
    item_first_ignited_code: Mapped[str | None] = mapped_column(String(10))
    cause_of_ignition_code: Mapped[str | None] = mapped_column(String(10))
    factor_contributing_code: Mapped[str | None] = mapped_column(String(10))
    human_factor_code: Mapped[str | None] = mapped_column(String(10))

    # Losses
    property_loss_dollars: Mapped[int] = mapped_column(Integer, default=0)
    contents_loss_dollars: Mapped[int] = mapped_column(Integer, default=0)
    property_value_dollars: Mapped[int | None] = mapped_column(Integer)
    contents_value_dollars: Mapped[int | None] = mapped_column(Integer)

    # Narrative
    narrative: Mapped[str | None] = mapped_column(Text)

    # Validation & export
    validation_issues: Mapped[list[dict[str, str]] | None] = mapped_column(JSONB)
    export_state: Mapped[str] = mapped_column(
        String(20), default=NERISExportState.DRAFT.value
    )
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    personnel: Mapped[list[FirePersonnelAssignment]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )
    apparatus: Mapped[list[FireApparatusRecord]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FirePersonnelAssignment(Base):
    """NERIS personnel involvement per incident."""

    __tablename__ = "fire_neris_personnel"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fire_neris_incidents.id"), nullable=False
    )
    member_id: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_code: Mapped[str | None] = mapped_column(String(10))
    injury: Mapped[bool] = mapped_column(Boolean, default=False)
    injury_type_code: Mapped[str | None] = mapped_column(String(10))

    incident: Mapped[FireIncident] = relationship(back_populates="personnel")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FireApparatusRecord(Base):
    """NERIS apparatus/unit response record per incident."""

    __tablename__ = "fire_neris_apparatus"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fire_neris_incidents.id"), nullable=False
    )
    unit_id: Mapped[str] = mapped_column(String(30), nullable=False)
    apparatus_type_code: Mapped[str | None] = mapped_column(String(10))
    dispatch_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enroute_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clear_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actions_taken: Mapped[list | None] = mapped_column(JSONB)
    personnel_count: Mapped[int] = mapped_column(Integer, default=0)

    incident: Mapped[FireIncident] = relationship(back_populates="apparatus")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FirePreplan(Base):
    """Pre-incident plan for a building/structure."""

    __tablename__ = "fire_preplans_v2"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    occupancy_type: Mapped[str | None] = mapped_column(String(50))
    stories: Mapped[int | None] = mapped_column(Integer)
    construction_type: Mapped[str | None] = mapped_column(String(50))
    sprinkler_system: Mapped[bool] = mapped_column(Boolean, default=False)
    standpipe: Mapped[bool] = mapped_column(Boolean, default=False)
    fire_alarm_system: Mapped[bool] = mapped_column(Boolean, default=False)
    hazards: Mapped[dict | None] = mapped_column(JSONB)
    contacts: Mapped[dict | None] = mapped_column(JSONB)
    floor_plans_s3_keys: Mapped[list | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FireHydrant(Base):
    """Hydrant inventory with geospatial data."""

    __tablename__ = "fire_hydrants_v2"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    hydrant_number: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    flow_rate_gpm: Mapped[int | None] = mapped_column(Integer)
    static_pressure_psi: Mapped[int | None] = mapped_column(Integer)
    hydrant_type: Mapped[str | None] = mapped_column(String(30))
    color_code: Mapped[str | None] = mapped_column(String(20))
    in_service: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FireInspection(Base):
    """Structure inspection tracking."""

    __tablename__ = "fire_inspections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    preplan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fire_preplans_v2.id")
    )
    inspector_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(30), default=FireInspectionStatus.SCHEDULED.value
    )
    findings: Mapped[dict | None] = mapped_column(JSONB)
    deficiencies: Mapped[list | None] = mapped_column(JSONB)
    corrective_due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    photos_s3_keys: Mapped[list | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NERISExportJob(Base):
    """Tracks NERIS batch exports to the state."""

    __tablename__ = "neris_export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    state: Mapped[str] = mapped_column(
        String(20), default=NERISExportState.DRAFT.value
    )
    incident_ids: Mapped[list] = mapped_column(JSONB, default=list)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_results: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB)
    export_file_s3_key: Mapped[str | None] = mapped_column(String(500))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_blob: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
