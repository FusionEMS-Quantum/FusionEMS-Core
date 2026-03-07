"""Tests for the Incident State Machine service."""
import pytest

from core_app.services.incident_state_machine import (
    IncidentService,
    IncidentSeverity,
    IncidentState,
    IncidentTransitionError,
)


@pytest.fixture
def svc() -> IncidentService:
    return IncidentService()


def test_create_incident(svc: IncidentService) -> None:
    incident = svc.create(
        tenant_id="t1",
        title="DB Latency Spike",
        severity=IncidentSeverity.HIGH,
        source="PostgreSQL",
    )
    assert incident.state == IncidentState.DETECTED
    assert incident.tenant_id == "t1"
    assert incident.severity == IncidentSeverity.HIGH
    assert len(incident.timeline) == 1


def test_valid_transition_detected_to_ack(svc: IncidentService) -> None:
    incident = svc.create(tenant_id="t1", title="Test", severity=IncidentSeverity.MEDIUM)
    updated = svc.transition(
        incident_id=incident.id,
        target_state=IncidentState.ACKNOWLEDGED,
        actor="user1",
        note="I see it",
    )
    assert updated.state == IncidentState.ACKNOWLEDGED
    assert len(updated.timeline) == 2


def test_full_lifecycle(svc: IncidentService) -> None:
    incident = svc.create(tenant_id="t1", title="Outage", severity=IncidentSeverity.CRITICAL)
    svc.transition(incident_id=incident.id, target_state=IncidentState.ACKNOWLEDGED, actor="a")
    svc.transition(incident_id=incident.id, target_state=IncidentState.INVESTIGATING, actor="a")
    svc.transition(incident_id=incident.id, target_state=IncidentState.MITIGATING, actor="a")
    svc.transition(incident_id=incident.id, target_state=IncidentState.RESOLVED, actor="a", note="Fixed")
    svc.transition(incident_id=incident.id, target_state=IncidentState.POSTMORTEM, actor="a")
    assert incident.state == IncidentState.POSTMORTEM
    assert incident.resolved_at is not None
    assert len(incident.timeline) == 6


def test_invalid_transition_raises(svc: IncidentService) -> None:
    incident = svc.create(tenant_id="t1", title="Test", severity=IncidentSeverity.LOW)
    with pytest.raises(IncidentTransitionError):
        svc.transition(incident_id=incident.id, target_state=IncidentState.RESOLVED, actor="a")


def test_list_active_excludes_resolved(svc: IncidentService) -> None:
    i1 = svc.create(tenant_id="t1", title="Active", severity=IncidentSeverity.HIGH)
    i2 = svc.create(tenant_id="t1", title="Resolved", severity=IncidentSeverity.LOW)
    svc.transition(incident_id=i2.id, target_state=IncidentState.ACKNOWLEDGED, actor="a")
    svc.transition(incident_id=i2.id, target_state=IncidentState.INVESTIGATING, actor="a")
    svc.transition(incident_id=i2.id, target_state=IncidentState.RESOLVED, actor="a")
    active = svc.list_active("t1")
    assert len(active) == 1
    assert active[0].id == i1.id


def test_tenant_isolation(svc: IncidentService) -> None:
    svc.create(tenant_id="t1", title="T1 Incident", severity=IncidentSeverity.HIGH)
    svc.create(tenant_id="t2", title="T2 Incident", severity=IncidentSeverity.LOW)
    assert len(svc.list_all("t1")) == 1
    assert len(svc.list_all("t2")) == 1
    assert len(svc.list_all("t3")) == 0


def test_get_missing_returns_none(svc: IncidentService) -> None:
    assert svc.get("nonexistent") is None


def test_transition_missing_incident_raises(svc: IncidentService) -> None:
    with pytest.raises(KeyError):
        svc.transition(incident_id="bad", target_state=IncidentState.ACKNOWLEDGED, actor="a")
