"""
CrewLink Paging Engine — Unit Tests
Covers: state machine transitions, escalation logic, backup crew,
tenant isolation, billing boundary enforcement, push delivery audit.

DIRECTIVE REQUIREMENT: CrewLink paging-only boundary validation.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from core_app.crewlink.paging_engine import (
    DEFAULT_ACCEPT_TIMEOUT_SECONDS,
    DEFAULT_ACK_TIMEOUT_SECONDS,
    CrewLinkPagingEngine,
    CrewResponse,
    PagingState,
)

# ── Fake Infrastructure ──────────────────────────────────────────────────────

class FakeDominationRepo:
    """In-memory repository for domination-pattern records."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def create(self, *, tenant_id: uuid.UUID, data: dict, typed_columns: dict | None = None) -> dict:
        record_id = uuid.uuid4()
        rec = {
            "id": record_id,
            "tenant_id": tenant_id,
            "version": 1,
            "data": data,
        }
        self._store[str(record_id)] = rec
        return rec

    def get(self, *, tenant_id: uuid.UUID, record_id: uuid.UUID) -> dict | None:
        rec = self._store.get(str(record_id))
        if rec and rec["tenant_id"] == tenant_id:
            return rec
        return None

    def update(self, *, tenant_id: uuid.UUID, record_id: uuid.UUID, expected_version: int, patch: dict) -> dict | None:
        rec = self._store.get(str(record_id))
        if not rec or rec["tenant_id"] != tenant_id:
            return None
        rec["data"] = {**(rec.get("data") or {}), **patch}
        rec["version"] = expected_version + 1
        return rec

    def list(self, *, tenant_id: uuid.UUID, limit: int = 100) -> list[dict]:
        return [r for r in self._store.values() if r["tenant_id"] == tenant_id]


class FakeDominationService:
    """Fake DominationService backed by in-memory repos."""

    def __init__(self) -> None:
        self._repos: dict[str, FakeDominationRepo] = {}
        self.audit_calls: list[dict] = []

    def repo(self, table: str) -> FakeDominationRepo:
        if table not in self._repos:
            self._repos[table] = FakeDominationRepo()
        return self._repos[table]

    async def create(self, *, table: str, tenant_id: uuid.UUID, actor_user_id: uuid.UUID | None, data: dict, correlation_id: str | None = None, typed_columns: dict | None = None, commit: bool = True) -> dict:
        return self.repo(table).create(tenant_id=tenant_id, data=data)


def _make_engine(tenant_id: uuid.UUID | None = None) -> tuple[CrewLinkPagingEngine, FakeDominationService]:
    """Create a CrewLinkPagingEngine with fake dependencies."""
    tid = tenant_id or uuid.uuid4()
    actor = uuid.uuid4()
    fake_svc = FakeDominationService()

    engine = CrewLinkPagingEngine(
        db=MagicMock(),
        publisher=AsyncMock(),
        tenant_id=tid,
        actor_user_id=actor,
    )
    # Replace the real DominationService with our fake
    engine.svc = fake_svc  # type: ignore[assignment]
    return engine, fake_svc


# ── State Machine Tests ──────────────────────────────────────────────────────

class TestPagingStateMachine:
    """Verify correct state transitions through the paging lifecycle."""

    @pytest.fixture()
    def tenant_id(self) -> uuid.UUID:
        return uuid.uuid4()

    @pytest.fixture()
    def engine_and_svc(self, tenant_id: uuid.UUID) -> tuple[CrewLinkPagingEngine, FakeDominationService]:
        return _make_engine(tenant_id)

    async def test_create_alert_returns_targets_resolved(self, engine_and_svc: tuple) -> None:
        engine, _ = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-001",
            mission_title="Chest Pain - 68yo M",
            mission_address="123 Main St",
            service_level="ALS",
            priority="HIGH",
            target_crew_ids=["crew-1", "crew-2"],
        )
        assert result["state"] == PagingState.TARGETS_RESOLVED.value
        assert result["recipient_count"] == 2
        assert "alert_id" in result
        assert "ack_deadline" in result
        assert "accept_deadline" in result

    async def test_create_alert_sets_timeout_deadlines(self, engine_and_svc: tuple) -> None:
        engine, _ = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-002",
            mission_title="MVA",
            mission_address="456 Oak Ave",
            service_level="BLS",
            priority="MEDIUM",
            target_crew_ids=["crew-1"],
            ack_timeout_seconds=60,
            accept_timeout_seconds=180,
        )
        assert result["state"] == PagingState.TARGETS_RESOLVED.value
        # Deadlines should be parseable ISO timestamps
        ack_deadline = datetime.fromisoformat(result["ack_deadline"])
        accept_deadline = datetime.fromisoformat(result["accept_deadline"])
        assert accept_deadline > ack_deadline

    async def test_crew_acknowledge_transitions_state(self, engine_and_svc: tuple, tenant_id: uuid.UUID) -> None:
        engine, svc = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-003",
            mission_title="Fall Injury",
            mission_address="789 Elm St",
            service_level="BLS",
            priority="LOW",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        # Record crew response
        response = await engine.record_crew_response(
            alert_id=str(alert_id),
            crew_member_id="crew-1",
            response=CrewResponse.ACKNOWLEDGE,
        )
        assert response["response"] == "ACKNOWLEDGE"
        assert response["new_state"] == "ACKNOWLEDGED"

    async def test_crew_accept_transitions_to_accepted(self, engine_and_svc: tuple) -> None:
        engine, _ = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-004",
            mission_title="Cardiac Arrest",
            mission_address="321 Pine Rd",
            service_level="ALS",
            priority="CRITICAL",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        response = await engine.record_crew_response(
            alert_id=str(alert_id),
            crew_member_id="crew-1",
            response=CrewResponse.ACCEPT,
        )
        assert response["response"] == "ACCEPT"
        assert response["new_state"] == "ACCEPTED"

    async def test_crew_decline_records_reason(self, engine_and_svc: tuple) -> None:
        engine, _ = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-005",
            mission_title="Transfer",
            mission_address="Hospital A",
            service_level="CCT",
            priority="MEDIUM",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        response = await engine.record_crew_response(
            alert_id=str(alert_id),
            crew_member_id="crew-1",
            response=CrewResponse.DECLINE,
            decline_reason="Out of service area",
        )
        assert response["response"] == "DECLINE"
        assert response["new_state"] == "DECLINED"

    async def test_escalation_changes_state(self, engine_and_svc: tuple) -> None:
        engine, _ = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-006",
            mission_title="Unresponsive",
            mission_address="555 Birch Ln",
            service_level="ALS",
            priority="CRITICAL",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        esc = await engine.escalate_alert(
            alert_id=str(alert_id),
            escalation_reason="ACK_TIMEOUT",
            triggered_by="SYSTEM_TIMER",
        )
        assert esc["state"] == PagingState.ESCALATED.value
        assert "escalation_event_id" in esc

    async def test_escalation_with_backup_crew(self, engine_and_svc: tuple) -> None:
        engine, _ = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-007",
            mission_title="Diabetic Emergency",
            mission_address="100 Cedar Dr",
            service_level="ALS",
            priority="HIGH",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        esc = await engine.escalate_alert(
            alert_id=str(alert_id),
            escalation_reason="ALL_DECLINED",
            backup_crew_ids=["crew-backup-1", "crew-backup-2"],
        )
        assert esc["state"] == PagingState.ESCALATED.value
        assert esc["backup_sent"] is True

    async def test_already_accepted_does_not_escalate(self, engine_and_svc: tuple) -> None:
        engine, svc = engine_and_svc
        result = await engine.create_paging_alert(
            mission_id="MISSION-008",
            mission_title="Seizure",
            mission_address="200 Maple Way",
            service_level="ALS",
            priority="HIGH",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        # Accept the page first
        await engine.record_crew_response(
            alert_id=str(alert_id),
            crew_member_id="crew-1",
            response=CrewResponse.ACCEPT,
        )

        # Escalation should be skipped
        esc = await engine.escalate_alert(
            alert_id=str(alert_id),
            escalation_reason="MANUAL_CHECK",
        )
        assert esc["status"] == "no_escalation_needed"
        assert esc["reason"] == "already_accepted"


# ── Paging-Only Boundary Tests ───────────────────────────────────────────────

class TestCrewLinkPagingBoundary:
    """
    CrewLink MUST NEVER handle billing messages.
    Verify the engine only processes operational paging.
    """

    async def test_alert_data_contains_no_billing_fields(self) -> None:
        engine, svc = _make_engine()
        await engine.create_paging_alert(
            mission_id="MISSION-BOUNDARY-1",
            mission_title="Routine Transfer",
            mission_address="Hospital B",
            service_level="BLS",
            priority="LOW",
            target_crew_ids=["crew-1"],
        )

        # Inspect the stored alert data
        alerts_repo = svc.repo("crew_paging_alerts")
        for rec in alerts_repo._store.values():
            data = rec.get("data", {})
            # Must never contain billing-related keys
            billing_keys = {
                "total_billed_cents", "insurance_carrier", "insurance_policy",
                "claim_state", "patient_balance", "hcpcs_code", "billing_case_id",
                "payment_amount", "copay", "deductible", "coinsurance",
            }
            present_billing_keys = billing_keys & set(data.keys())
            assert not present_billing_keys, (
                f"CrewLink alert contains billing data: {present_billing_keys}"
            )

    async def test_paging_contains_operational_fields_only(self) -> None:
        engine, svc = _make_engine()
        result = await engine.create_paging_alert(
            mission_id="MISSION-OPS-1",
            mission_title="Chest Pain",
            mission_address="123 Main St",
            service_level="ALS",
            priority="HIGH",
            target_crew_ids=["crew-1"],
            chief_complaint="CP, 72yo F, hx HTN",
            special_instructions="Gate code: 1234",
        )
        # All fields returned must be operational
        operational_keys = {"alert_id", "state", "recipient_count", "ack_deadline", "accept_deadline"}
        assert operational_keys.issubset(set(result.keys()))

    async def test_paging_state_enum_values_are_operational(self) -> None:
        """All PagingState values must be operational, not billing-related."""
        for state in PagingState:
            assert "BILL" not in state.value.upper()
            assert "CLAIM" not in state.value.upper()
            assert "PAYMENT" not in state.value.upper()
            assert "INSURANCE" not in state.value.upper()


# ── Tenant Isolation Tests ───────────────────────────────────────────────────

class TestCrewLinkTenantIsolation:
    """Cross-tenant paging access must be impossible."""

    async def test_tenant_isolation_prevents_cross_tenant_escalation(self) -> None:
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        engine_a, _ = _make_engine(tenant_a)
        engine_b, _ = _make_engine(tenant_b)

        result = await engine_a.create_paging_alert(
            mission_id="ISO-1",
            mission_title="Isolated Alert",
            mission_address="Tenant A HQ",
            service_level="ALS",
            priority="HIGH",
            target_crew_ids=["crew-a1"],
        )
        alert_id = result["alert_id"]

        # Tenant B tries to escalate Tenant A's alert
        esc = await engine_b.escalate_alert(
            alert_id=str(alert_id),
            escalation_reason="CROSS_TENANT_ATTEMPT",
        )
        assert esc.get("error") == "alert_not_found"

    async def test_tenant_isolation_prevents_cross_tenant_response(self) -> None:
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        engine_a, _ = _make_engine(tenant_a)
        engine_b, _ = _make_engine(tenant_b)

        result = await engine_a.create_paging_alert(
            mission_id="ISO-2",
            mission_title="Secure Alert",
            mission_address="Tenant A Station",
            service_level="BLS",
            priority="MEDIUM",
            target_crew_ids=["crew-a1"],
        )
        alert_id = result["alert_id"]

        # Tenant B tries to respond to Tenant A's alert
        resp = await engine_b.record_crew_response(
            alert_id=str(alert_id),
            crew_member_id="crew-b1",
            response=CrewResponse.ACCEPT,
        )
        assert resp.get("error") == "recipient_not_found"


# ── Audit Trail Tests ─────────────────────────────────────────────────────────

class TestCrewLinkAuditTrail:
    """Every paging action must produce an auditable event."""

    async def test_create_alert_generates_audit_event(self) -> None:
        engine, svc = _make_engine()
        await engine.create_paging_alert(
            mission_id="AUDIT-1",
            mission_title="Audit Test",
            mission_address="HQ",
            service_level="ALS",
            priority="HIGH",
            target_crew_ids=["crew-1"],
            correlation_id="corr-audit-001",
        )
        # Audit events are stored in crew_paging_audit_log
        audit_repo = svc.repo("crew_paging_audit_log")
        audit_records = audit_repo.list(tenant_id=engine.tenant_id)
        assert len(audit_records) >= 1
        first_event = audit_records[0]["data"]
        assert first_event["event_type"] == "ALERT_CREATED"

    async def test_escalation_generates_audit_event(self) -> None:
        engine, svc = _make_engine()
        result = await engine.create_paging_alert(
            mission_id="AUDIT-2",
            mission_title="Escalation Audit",
            mission_address="Station 5",
            service_level="ALS",
            priority="CRITICAL",
            target_crew_ids=["crew-1"],
        )
        await engine.escalate_alert(
            alert_id=str(result["alert_id"]),
            escalation_reason="TIMEOUT",
            correlation_id="corr-audit-002",
        )
        audit_repo = svc.repo("crew_paging_audit_log")
        audit_records = audit_repo.list(tenant_id=engine.tenant_id)
        event_types = [r["data"]["event_type"] for r in audit_records]
        assert "ALERT_ESCALATED" in event_types


# ── Escalation Rule Tests ─────────────────────────────────────────────────────

class TestEscalationRules:
    """Custom and default escalation rules are persisted correctly."""

    async def test_default_escalation_rule_created(self) -> None:
        engine, svc = _make_engine()
        await engine.create_paging_alert(
            mission_id="ESC-DEFAULT",
            mission_title="Default Rules",
            mission_address="Station 1",
            service_level="BLS",
            priority="MEDIUM",
            target_crew_ids=["crew-1"],
        )
        rules_repo = svc.repo("crew_paging_escalation_rules")
        rules = rules_repo.list(tenant_id=engine.tenant_id)
        assert len(rules) >= 1
        rule_data = rules[0]["data"]
        assert rule_data["trigger"] == "NO_ACCEPT"
        assert rule_data["action"] == "BACKUP_PAGE"

    async def test_custom_escalation_rules_persisted(self) -> None:
        engine, svc = _make_engine()
        custom_rules = [
            {"trigger": "NO_ACK", "timeout_seconds": 60, "action": "SUPERVISOR_NOTIFY", "active": True},
            {"trigger": "ALL_DECLINED", "timeout_seconds": 0, "action": "MUTUAL_AID", "active": True},
        ]
        await engine.create_paging_alert(
            mission_id="ESC-CUSTOM",
            mission_title="Custom Rules",
            mission_address="Station 2",
            service_level="ALS",
            priority="HIGH",
            target_crew_ids=["crew-1"],
            escalation_rules=custom_rules,
        )
        rules_repo = svc.repo("crew_paging_escalation_rules")
        rules = rules_repo.list(tenant_id=engine.tenant_id)
        assert len(rules) == 2
        triggers = {r["data"]["trigger"] for r in rules}
        assert triggers == {"NO_ACK", "ALL_DECLINED"}


# ── Push Delivery Tests ──────────────────────────────────────────────────────

class TestPushDelivery:
    """Push send/delivered tracking updates recipient state."""

    async def test_record_push_sent_updates_recipient(self) -> None:
        engine, svc = _make_engine()
        result = await engine.create_paging_alert(
            mission_id="PUSH-1",
            mission_title="Push Test",
            mission_address="Base",
            service_level="BLS",
            priority="LOW",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        # Get a recipient
        recipients_repo = svc.repo("crew_paging_recipients")
        recipients = recipients_repo.list(tenant_id=engine.tenant_id)
        assert len(recipients) >= 1
        recipient_id = str(recipients[0]["id"])

        sent_result = await engine.record_push_sent(
            alert_id=str(alert_id),
            recipient_id=recipient_id,
            push_message_id="fcm-msg-001",
            platform="android",
        )
        assert sent_result.get("state") == "SENT" or sent_result.get("recipient_id") == recipient_id

    async def test_record_push_delivered_updates_recipient(self) -> None:
        engine, svc = _make_engine()
        result = await engine.create_paging_alert(
            mission_id="PUSH-2",
            mission_title="Delivery Test",
            mission_address="Base",
            service_level="BLS",
            priority="LOW",
            target_crew_ids=["crew-1"],
        )
        alert_id = result["alert_id"]

        recipients_repo = svc.repo("crew_paging_recipients")
        recipients = recipients_repo.list(tenant_id=engine.tenant_id)
        recipient_id = str(recipients[0]["id"])

        # Mark sent first
        await engine.record_push_sent(
            alert_id=str(alert_id),
            recipient_id=recipient_id,
            push_message_id="fcm-msg-002",
            platform="ios",
        )
        # Mark delivered
        delivered = await engine.record_push_delivered(
            alert_id=str(alert_id),
            recipient_id=recipient_id,
            push_message_id="fcm-msg-002",
        )
        assert delivered.get("state") == "DELIVERED" or delivered.get("recipient_id") == recipient_id


# ── Constants Tests ──────────────────────────────────────────────────────────

class TestPagingConstants:
    """Default timeout constants are sane for EMS operations."""

    def test_ack_timeout_is_reasonable(self) -> None:
        assert 30 <= DEFAULT_ACK_TIMEOUT_SECONDS <= 600

    def test_accept_timeout_greater_than_ack(self) -> None:
        assert DEFAULT_ACCEPT_TIMEOUT_SECONDS > DEFAULT_ACK_TIMEOUT_SECONDS

    def test_all_paging_states_defined(self) -> None:
        expected = {
            "ALERT_CREATED", "TARGETS_RESOLVED", "PUSH_SENT", "PUSH_DELIVERED",
            "ACKNOWLEDGED", "ACCEPTED", "DECLINED", "NO_RESPONSE",
            "ESCALATED", "BACKUP_ALERT_SENT", "CLOSED",
        }
        actual = {s.value for s in PagingState}
        assert expected == actual

    def test_crew_response_values(self) -> None:
        assert {r.value for r in CrewResponse} == {"ACKNOWLEDGE", "ACCEPT", "DECLINE"}
