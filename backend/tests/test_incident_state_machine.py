"""Tests for the Incident State Machine service."""
# pylint: disable=redefined-outer-name

import pytest

from core_app.services.incident_state_machine import (
    IncidentService,
    IncidentSeverity,
    IncidentState,
    IncidentTransitionError,
)


@pytest.fixture
def incident_service() -> IncidentService:
    return IncidentService()


def test_create_incident(incident_service: IncidentService) -> None:
    incident = incident_service.create(
        tenant_id="t1",
        title="DB Latency Spike",
        severity=IncidentSeverity.HIGH,
        source="PostgreSQL",
    )
    assert incident.state == IncidentState.DETECTED
    assert incident.tenant_id == "t1"
    assert incident.severity == IncidentSeverity.HIGH
    assert len(incident.timeline) == 1


def test_valid_transition_detected_to_ack(incident_service: IncidentService) -> None:
    incident = incident_service.create(tenant_id="t1", title="Test", severity=IncidentSeverity.MEDIUM)
    updated = incident_service.transition(
        incident_id=incident.id,
        target_state=IncidentState.ACKNOWLEDGED,
        actor="user1",
        note="I see it",
    )
    assert updated.state == IncidentState.ACKNOWLEDGED
    assert len(updated.timeline) == 2


def test_full_lifecycle(incident_service: IncidentService) -> None:
    incident = incident_service.create(tenant_id="t1", title="Outage", severity=IncidentSeverity.CRITICAL)
    incident_service.transition(incident_id=incident.id, target_state=IncidentState.ACKNOWLEDGED, actor="a")
    incident_service.transition(incident_id=incident.id, target_state=IncidentState.INVESTIGATING, actor="a")
    incident_service.transition(incident_id=incident.id, target_state=IncidentState.MITIGATING, actor="a")
    incident_service.transition(incident_id=incident.id, target_state=IncidentState.RESOLVED, actor="a", note="Fixed")
    incident_service.transition(incident_id=incident.id, target_state=IncidentState.POSTMORTEM, actor="a")
    assert incident.state == IncidentState.POSTMORTEM
    assert incident.resolved_at is not None
    assert len(incident.timeline) == 6


def test_invalid_transition_raises(incident_service: IncidentService) -> None:
    incident = incident_service.create(tenant_id="t1", title="Test", severity=IncidentSeverity.LOW)
    with pytest.raises(IncidentTransitionError):
        incident_service.transition(incident_id=incident.id, target_state=IncidentState.RESOLVED, actor="a")


def test_list_active_excludes_resolved(incident_service: IncidentService) -> None:
    i1 = incident_service.create(tenant_id="t1", title="Active", severity=IncidentSeverity.HIGH)
    i2 = incident_service.create(tenant_id="t1", title="Resolved", severity=IncidentSeverity.LOW)
    incident_service.transition(incident_id=i2.id, target_state=IncidentState.ACKNOWLEDGED, actor="a")
    incident_service.transition(incident_id=i2.id, target_state=IncidentState.INVESTIGATING, actor="a")
    incident_service.transition(incident_id=i2.id, target_state=IncidentState.RESOLVED, actor="a")
    active = incident_service.list_active("t1")
    assert len(active) == 1
    assert active[0].id == i1.id


def test_tenant_isolation(incident_service: IncidentService) -> None:
    incident_service.create(tenant_id="t1", title="T1 Incident", severity=IncidentSeverity.HIGH)
    incident_service.create(tenant_id="t2", title="T2 Incident", severity=IncidentSeverity.LOW)
    assert len(incident_service.list_all("t1")) == 1
    assert len(incident_service.list_all("t2")) == 1
    assert len(incident_service.list_all("t3")) == 0


def test_get_missing_returns_none(incident_service: IncidentService) -> None:
    assert incident_service.get("nonexistent") is None


def test_transition_missing_incident_raises(incident_service: IncidentService) -> None:
    with pytest.raises(KeyError):
        incident_service.transition(incident_id="bad", target_state=IncidentState.ACKNOWLEDGED, actor="a")
