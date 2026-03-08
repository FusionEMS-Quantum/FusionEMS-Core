# pylint: disable=not-callable
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin


class FireOpsState(enum.StrEnum):
    PREPLAN_AVAILABLE = "PREPLAN_AVAILABLE"
    PREPLAN_MISSING = "PREPLAN_MISSING"
    HAZARD_FLAGGED = "HAZARD_FLAGGED"
    WATER_REFERENCE_READY = "WATER_REFERENCE_READY"
    COMMAND_REVIEW_REQUIRED = "COMMAND_REVIEW_REQUIRED"


class FlightOpsState(enum.StrEnum):
    AIR_ASSET_READY = "AIR_ASSET_READY"
    DUTY_WARNING = "DUTY_WARNING"
    LZ_PENDING = "LZ_PENDING"
    LZ_CONFIRMED = "LZ_CONFIRMED"
    MISSION_ACTIVE = "MISSION_ACTIVE"
    MISSION_DELAYED = "MISSION_DELAYED"
    AIR_ASSET_UNAVAILABLE = "AIR_ASSET_UNAVAILABLE"


class SpecialtyTransportState(enum.StrEnum):
    STANDARD = "STANDARD"
    SPECIALTY_FLAGGED = "SPECIALTY_FLAGGED"
    EQUIPMENT_PENDING = "EQUIPMENT_PENDING"
    CREW_PENDING = "CREW_PENDING"
    READY = "READY"
    BLOCKED = "BLOCKED"


class MissionPacketState(enum.StrEnum):
    NOT_PREPARED = "NOT_PREPARED"
    DRAFTED = "DRAFTED"
    READY = "READY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class PremisePreplan(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "premise_preplans"

    premise_name: Mapped[str] = mapped_column(String(255), nullable=False)
    premise_address: Mapped[str] = mapped_column(String(512), nullable=False)
    state: Mapped[FireOpsState] = mapped_column(
        Enum(FireOpsState),
        nullable=False,
        default=FireOpsState.PREPLAN_MISSING,
    )
    source_system: Mapped[str] = mapped_column(String(128), nullable=False, default="manual")
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occupancy_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    building_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    knox_fdc_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    command_support_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    accountability_references: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class HydrantReference(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "hydrant_references"

    premise_preplan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("premise_preplans.id"),
        nullable=False,
        index=True,
    )
    hydrant_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    static_pressure_psi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flow_rate_gpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    in_service: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WaterSupplyNote(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "water_supply_notes"

    premise_preplan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("premise_preplans.id"),
        nullable=False,
        index=True,
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HazardFlag(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "hazard_flags"

    premise_preplan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("premise_preplans.id"),
        nullable=False,
        index=True,
    )
    hazard_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class FireOpsAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "fire_ops_audit_events"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)


class AirAsset(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "air_assets"

    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    callsign: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tail_number: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[FlightOpsState] = mapped_column(Enum(FlightOpsState), nullable=False, default=FlightOpsState.AIR_ASSET_READY)
    readiness_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    duty_minutes_remaining: Mapped[int | None] = mapped_column(Integer, nullable=True)
    capability_profile: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class FlightMission(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "flight_missions"

    mission_number: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    air_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("air_assets.id"), nullable=True, index=True)
    state: Mapped[FlightOpsState] = mapped_column(Enum(FlightOpsState), nullable=False, default=FlightOpsState.LZ_PENDING)
    origin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receiving_facility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FlightLegEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "flight_leg_events"

    flight_mission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("flight_missions.id"), nullable=False, index=True)
    leg_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)


class LandingZoneRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "landing_zone_records"

    flight_mission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("flight_missions.id"), nullable=False, index=True)
    lz_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[FlightOpsState] = mapped_column(Enum(FlightOpsState), nullable=False, default=FlightOpsState.LZ_PENDING)
    approach_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    hazards: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DutyTimeFlag(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "duty_time_flags"

    air_asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("air_assets.id"), nullable=True, index=True)
    crew_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FlightOpsAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "flight_ops_audit_events"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)


class SpecialtyMissionRequirement(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "specialty_mission_requirements"

    mission_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    requirement_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[SpecialtyTransportState] = mapped_column(Enum(SpecialtyTransportState), nullable=False, default=SpecialtyTransportState.SPECIALTY_FLAGGED)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SpecialtyEquipmentCheck(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "specialty_equipment_checks"

    mission_requirement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("specialty_mission_requirements.id"), nullable=False, index=True)
    equipment_code: Mapped[str] = mapped_column(String(128), nullable=False)
    required_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[SpecialtyTransportState] = mapped_column(Enum(SpecialtyTransportState), nullable=False, default=SpecialtyTransportState.EQUIPMENT_PENDING)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MissionFitScore(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "mission_fit_scores"

    mission_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    unit_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    crew_fit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    equipment_fit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[SpecialtyTransportState] = mapped_column(Enum(SpecialtyTransportState), nullable=False, default=SpecialtyTransportState.READY)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class SpecialtyTransportAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "specialty_transport_audit_events"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)


class MissionPacket(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "mission_packets"

    mission_ref: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state: Mapped[MissionPacketState] = mapped_column(Enum(MissionPacketState), nullable=False, default=MissionPacketState.NOT_PREPARED)
    source_record_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class MissionPacketSection(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "mission_packet_sections"

    mission_packet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mission_packets.id"), nullable=False, index=True)
    section_type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class MissionPacketDelivery(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "mission_packet_deliveries"

    mission_packet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("mission_packets.id"), nullable=False, index=True)
    destination_type: Mapped[str] = mapped_column(String(64), nullable=False)
    destination_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[MissionPacketState] = mapped_column(Enum(MissionPacketState), nullable=False, default=MissionPacketState.DRAFTED)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class MissionPacketAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "mission_packet_audit_events"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False)
