"""Incident State Machine — deterministic incident lifecycle management.

States: DETECTED → ACKNOWLEDGED → INVESTIGATING → MITIGATING → RESOLVED → POSTMORTEM
All transitions are audited and tenant-scoped.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IncidentState(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    MITIGATING = "MITIGATING"
    RESOLVED = "RESOLVED"
    POSTMORTEM = "POSTMORTEM"


class IncidentSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Valid state transitions
ALLOWED_TRANSITIONS: dict[IncidentState, set[IncidentState]] = {
    IncidentState.DETECTED: {IncidentState.ACKNOWLEDGED},
    IncidentState.ACKNOWLEDGED: {IncidentState.INVESTIGATING},
    IncidentState.INVESTIGATING: {IncidentState.MITIGATING, IncidentState.RESOLVED},
    IncidentState.MITIGATING: {IncidentState.RESOLVED},
    IncidentState.RESOLVED: {IncidentState.POSTMORTEM},
    IncidentState.POSTMORTEM: set(),
}


class IncidentEvent(BaseModel):
    timestamp: str
    from_state: IncidentState
    to_state: IncidentState
    actor: str
    note: str = ""


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    title: str
    severity: IncidentSeverity
    state: IncidentState = IncidentState.DETECTED
    source: str = ""
    description: str = ""
    assigned_to: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: str | None = None
    timeline: list[IncidentEvent] = Field(default_factory=list)


class IncidentTransitionError(Exception):
    def __init__(self, current: IncidentState, target: IncidentState) -> None:
        super().__init__(f"Invalid transition: {current.value} → {target.value}")
        self.current = current
        self.target = target


class IncidentService:
    """In-memory incident state machine for platform reliability tracking.

    Production deployment should back this with a persistent store (PostgreSQL).
    This implementation provides the correct state machine semantics.
    """

    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}

    def create(
        self,
        *,
        tenant_id: str,
        title: str,
        severity: IncidentSeverity,
        source: str = "",
        description: str = "",
    ) -> Incident:
        incident = Incident(
            tenant_id=tenant_id,
            title=title,
            severity=severity,
            source=source,
            description=description,
        )
        incident.timeline.append(
            IncidentEvent(
                timestamp=incident.created_at,
                from_state=IncidentState.DETECTED,
                to_state=IncidentState.DETECTED,
                actor="system",
                note="Incident created",
            )
        )
        self._incidents[incident.id] = incident
        logger.info(
            "Incident created: %s [%s] %s",
            incident.id,
            severity.value,
            title,
            extra={"extra_fields": {"tenant_id": tenant_id, "incident_id": incident.id}},
        )
        return incident

    def transition(
        self,
        *,
        incident_id: str,
        target_state: IncidentState,
        actor: str,
        note: str = "",
    ) -> Incident:
        incident = self._incidents.get(incident_id)
        if not incident:
            raise KeyError(f"Incident {incident_id} not found")

        if target_state not in ALLOWED_TRANSITIONS.get(incident.state, set()):
            raise IncidentTransitionError(incident.state, target_state)

        from_state = incident.state
        now = datetime.now(timezone.utc).isoformat()

        incident.state = target_state
        incident.updated_at = now
        if target_state == IncidentState.RESOLVED:
            incident.resolved_at = now

        incident.timeline.append(
            IncidentEvent(
                timestamp=now,
                from_state=from_state,
                to_state=target_state,
                actor=actor,
                note=note,
            )
        )

        logger.info(
            "Incident %s transitioned: %s → %s by %s",
            incident_id,
            from_state.value,
            target_state.value,
            actor,
            extra={"extra_fields": {"incident_id": incident_id, "tenant_id": incident.tenant_id}},
        )
        return incident

    def get(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def list_active(self, tenant_id: str) -> list[Incident]:
        terminal = {IncidentState.RESOLVED, IncidentState.POSTMORTEM}
        return [
            i
            for i in self._incidents.values()
            if i.tenant_id == tenant_id and i.state not in terminal
        ]

    def list_all(self, tenant_id: str) -> list[Incident]:
        return [i for i in self._incidents.values() if i.tenant_id == tenant_id]


# Singleton for application lifetime. Production should be injected via DI.
_incident_service: IncidentService | None = None


def get_incident_service() -> IncidentService:
    global _incident_service
    if _incident_service is None:
        _incident_service = IncidentService()
    return _incident_service
