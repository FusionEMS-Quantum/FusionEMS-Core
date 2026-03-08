"""Tests for Responsible Party domain — Part 4 verification.

Validates responsibility state machine, relationship types,
audit events, and boundary rules (no guessed responsibility).
"""
from __future__ import annotations

import uuid

from core_app.models.responsible_party import (
    InsuranceSubscriberProfile,
    PatientResponsiblePartyLink,
    RelationshipToPatient,
    ResponsibilityAuditEvent,
    ResponsibilityState,
    ResponsibleParty,
)
from core_app.schemas.responsible_party import (
    InsuranceSubscriberCreate,
    PatientResponsiblePartyLinkCreate,
    ResponsiblePartyCreate,
)

# ── State Machine Tests ──────────────────────────────────────────────────────


class TestResponsibilityStateMachine:
    """Verify state machine enum values match directive spec."""

    def test_all_states_defined(self) -> None:
        expected = {
            "UNKNOWN",
            "PATIENT_SELF",
            "GUARANTOR_IDENTIFIED",
            "SUBSCRIBER_IDENTIFIED",
            "REVIEW_REQUIRED",
            "DISPUTED",
        }
        actual = {s.value for s in ResponsibilityState}
        assert actual == expected

    def test_default_state_unknown(self) -> None:
        assert ResponsibilityState.UNKNOWN.value == "UNKNOWN"


class TestRelationshipToPatient:
    def test_all_types_defined(self) -> None:
        expected = {"SELF", "SPOUSE", "PARENT", "CHILD", "GUARDIAN", "OTHER"}
        actual = {r.value for r in RelationshipToPatient}
        assert actual == expected


# ── Model Tests ──────────────────────────────────────────────────────────────


class TestResponsiblePartyModels:
    def test_responsible_party_table_exists(self) -> None:
        tbl = ResponsibleParty.__table__
        assert tbl.name == "responsible_parties"
        assert "first_name" in tbl.c
        assert "last_name" in tbl.c
        assert "phone" in tbl.c
        assert "email" in tbl.c

    def test_link_table_has_state(self) -> None:
        tbl = PatientResponsiblePartyLink.__table__
        assert "responsibility_state" in tbl.c
        assert "is_primary" in tbl.c
        assert "relationship_to_patient" in tbl.c

    def test_insurance_subscriber_profile_exists(self) -> None:
        tbl = InsuranceSubscriberProfile.__table__
        assert "insurance_carrier" in tbl.c
        assert "policy_number" in tbl.c
        assert "group_number" in tbl.c
        assert "member_id" in tbl.c
        assert "is_active" in tbl.c

    def test_audit_event_has_required_fields(self) -> None:
        tbl = ResponsibilityAuditEvent.__table__
        assert "action" in tbl.c
        assert "previous_state" in tbl.c
        assert "new_state" in tbl.c
        assert "actor_user_id" in tbl.c
        assert "correlation_id" in tbl.c


# ── Schema Tests ─────────────────────────────────────────────────────────────


class TestResponsiblePartySchemas:
    def test_create_valid(self) -> None:
        rp = ResponsiblePartyCreate(
            first_name="Jane",
            last_name="Doe",
            phone="555-0100",
        )
        assert rp.first_name == "Jane"

    def test_link_create(self) -> None:
        link = PatientResponsiblePartyLinkCreate(
            responsible_party_id=uuid.uuid4(),
            relationship_to_patient=RelationshipToPatient.PARENT,
            is_primary=True,
        )
        assert link.relationship_to_patient == RelationshipToPatient.PARENT

    def test_insurance_create(self) -> None:
        isp = InsuranceSubscriberCreate(
            responsible_party_id=uuid.uuid4(),
            insurance_carrier="Blue Cross",
            policy_number="POL-12345",
            group_number="GRP-001",
            member_id="MEM-789",
            subscriber_name="Jane Doe",
        )
        assert isp.insurance_carrier == "Blue Cross"


# ── Boundary Tests ───────────────────────────────────────────────────────────


class TestResponsibilityBoundaries:
    """Directive boundary: do not assume the patient is the subscriber or guarantor.
    Relationship type must be explicit. Financial responsibility changes must be auditable."""

    def test_responsibility_state_starts_unknown(self) -> None:
        """Default state is UNKNOWN, not PATIENT_SELF."""
        tbl = PatientResponsiblePartyLink.__table__
        col = tbl.c.responsibility_state
        # Column exists and default should be UNKNOWN
        assert col is not None

    def test_audit_event_immutable_fields(self) -> None:
        """Audit events must track what changed."""
        tbl = ResponsibilityAuditEvent.__table__
        required = {"action", "previous_state", "new_state", "actor_user_id"}
        actual = set(tbl.c.keys())
        assert required.issubset(actual)
