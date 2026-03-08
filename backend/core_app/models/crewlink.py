# ruff: noqa: I001

from datetime import datetime
from enum import StrEnum

# pylint: disable=unsubscriptable-object

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AlertState(StrEnum):
    """
    CREWLINK PAGING LIFECYCLE STATE MACHINE
    Defined in FINAL_BUILD_STATEMENT.md Section 5F.
    """
    PAGE_CREATED = "PAGE_CREATED"
    PAGE_SENT = "PAGE_SENT"
    PAGE_DELIVERED = "PAGE_DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    NO_RESPONSE = "NO_RESPONSE"
    ESCALATED = "ESCALATED"
    BACKUP_NOTIFIED = "BACKUP_NOTIFIED"
    CLOSED = "CLOSED"


class CrewPagingAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Operational Paging Alert (e.g., "Code 3 Response").
    Separate from Billing SMS. Uses Firebase/Native Push.
    """
    __tablename__ = "crew_paging_alerts"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    incident_id: Mapped[UUID | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)

    # Priority
    priority: Mapped[str] = mapped_column(String(16), default="ROUTINE", nullable=False) # EMERGENT, URGENT, ROUTINE

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # State
    status: Mapped[AlertState] = mapped_column(String(32), default=AlertState.PAGE_CREATED, nullable=False)
    dispatched_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)


class CrewPushDevice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Registered mobile device for a crew member.
    """
    __tablename__ = "crew_push_devices"

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False) # Linked to Users table
    device_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False) # FCM Token or APNS
    platform: Mapped[str] = mapped_column(String(16), default="ANDROID", nullable=False) # IOS, ANDROID

    last_active_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CrewPagingRecipient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual crew member targeted by an alert.
    """
    __tablename__ = "crew_paging_recipients"

    alert_id: Mapped[UUID] = mapped_column(ForeignKey("crew_paging_alerts.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    device_id: Mapped[UUID | None] = mapped_column(ForeignKey("crew_push_devices.id"), nullable=True) # Specific device used if known

    status: Mapped[str] = mapped_column(String(32), default="SENT", nullable=False) # SENT, DELIVERED, READ, ACKNOWLEDGED, ACCEPTED, DECLINED
    response_at: Mapped[datetime | None] = mapped_column(nullable=True)


class CrewMissionAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Active mission context for a crew.
    """
    __tablename__ = "crew_mission_assignments"

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), unique=True, nullable=False)

    assigned_crew_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False) # List of user IDs
    mission_status: Mapped[str] = mapped_column(String(32), default="ASSIGNED", nullable=False) # ASSIGNED, EN_ROUTE, ON_SCENE, TRANSPORTING, AT_DESTINATION, CLEAR

    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CrewPagingResponse(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Detailed response record from a crew member to a paging alert.
    Separate from recipient status to support multi-response workflows.
    """
    __tablename__ = "crew_paging_responses"

    alert_id: Mapped[UUID] = mapped_column(ForeignKey("crew_paging_alerts.id"), nullable=False, index=True)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("crew_paging_recipients.id"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    response_type: Mapped[str] = mapped_column(String(32), nullable=False)  # ACKNOWLEDGE, ACCEPT, DECLINE, EN_ROUTE, ON_SCENE
    response_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CrewPagingEscalationRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Configurable escalation rules for paging timeouts.
    Defines when and how to escalate if no crew responds.
    """
    __tablename__ = "crew_paging_escalation_rules"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)  # EMERGENT, URGENT, ROUTINE
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    escalation_target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # BACKUP_CREW, SUPERVISOR, ALL_AVAILABLE
    escalation_target_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    max_escalation_rounds: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CrewPagingEscalationEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks escalation events when pages timeout without response.
    Audit trail for operational accountability.
    """
    __tablename__ = "crew_paging_escalation_events"

    alert_id: Mapped[UUID] = mapped_column(ForeignKey("crew_paging_alerts.id"), nullable=False, index=True)
    rule_id: Mapped[UUID] = mapped_column(ForeignKey("crew_paging_escalation_rules.id"), nullable=False)

    escalation_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    escalated_to_user_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)  # TIMEOUT, NO_RESPONSE, ALL_DECLINED
    triggered_at: Mapped[datetime] = mapped_column(nullable=False)
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)


class CrewStatusEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Tracks crew status changes — availability, location, duty state.
    Used for dispatch optimization and operational visibility.
    """
    __tablename__ = "crew_status_events"

    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False)  # AVAILABLE, ON_MISSION, OFF_DUTY, BREAK, STANDBY
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="APP", nullable=False)  # APP, DISPATCH, SYSTEM, FATIGUE_ENGINE


class CrewPagingAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Comprehensive audit trail for all paging operations.
    Covers dispatches, responses, escalations, cancellations.
    """
    __tablename__ = "crew_paging_audit_events"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    alert_id: Mapped[UUID | None] = mapped_column(ForeignKey("crew_paging_alerts.id"), nullable=True)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # ALERT_CREATED, DISPATCHED, ACK_RECEIVED, ESCALATED, CANCELLED, COMPLETED
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)  # SYSTEM, DISPATCHER, CREW, SUPERVISOR
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_blob: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
