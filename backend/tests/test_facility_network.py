"""Tests for Facility Network domain — Part 5 verification.

Validates facility state machine, contact roles, friction flags,
service profiles, audit events, and relationship management.
"""
from __future__ import annotations

from core_app.models.facility import (
    Facility,
    FacilityAuditEvent,
    FacilityContact,
    FacilityContactRole,
    FacilityFrictionFlag,
    FacilityRelationshipNote,
    FacilityRelationshipState,
    FacilityServiceProfile,
    FacilityType,
    FrictionCategory,
)

# ── State Machine Tests ──────────────────────────────────────────────────────


class TestFacilityStateMachine:
    def test_all_states_defined(self) -> None:
        expected = {
            "ACTIVE",
            "LIMITED_RELATIONSHIP",
            "HIGH_FRICTION",
            "REVIEW_REQUIRED",
            "INACTIVE",
        }
        actual = {s.value for s in FacilityRelationshipState}
        assert actual == expected


class TestFacilityTypeEnum:
    def test_all_types_defined(self) -> None:
        expected = {
            "HOSPITAL", "SNF", "LTC", "REHAB", "DIALYSIS",
            "PSYCHIATRIC", "URGENT_CARE", "PHYSICIANS_OFFICE",
            "HOME_HEALTH", "OTHER",
        }
        actual = {t.value for t in FacilityType}
        assert actual == expected


class TestFacilityContactRoles:
    def test_all_roles_defined(self) -> None:
        expected = {
            "INTAKE_COORDINATOR", "NURSE", "SOCIAL_WORKER",
            "CASE_MANAGER", "CHARGE_NURSE", "ADMINISTRATOR",
            "BILLING_CONTACT", "DISPATCH_LIAISON", "OTHER",
        }
        actual = {r.value for r in FacilityContactRole}
        assert actual == expected


class TestFrictionCategories:
    def test_all_categories_defined(self) -> None:
        expected = {
            "WAIT_TIMES", "COMMUNICATION", "DOCUMENTATION",
            "BILLING_DISPUTES", "SAFETY_CONCERN", "STAFF_CONFLICT", "OTHER",
        }
        actual = {c.value for c in FrictionCategory}
        assert actual == expected


# ── Model Table Tests ────────────────────────────────────────────────────────


class TestFacilityModels:
    def test_facility_table(self) -> None:
        tbl = Facility.__table__
        assert tbl.name == "facilities"
        assert "name" in tbl.c
        assert "facility_type" in tbl.c
        assert "npi" in tbl.c
        assert "relationship_state" in tbl.c
        assert "address_line_1" in tbl.c
        assert "city" in tbl.c
        assert "state" in tbl.c
        assert "zip_code" in tbl.c
        assert "phone" in tbl.c
        assert "fax" in tbl.c
        assert "email" in tbl.c

    def test_facility_contact_table(self) -> None:
        tbl = FacilityContact.__table__
        assert "facility_id" in tbl.c
        assert "name" in tbl.c
        assert "role" in tbl.c
        assert "phone" in tbl.c
        assert "email" in tbl.c
        assert "preferred_contact_method" in tbl.c
        assert "is_active" in tbl.c

    def test_relationship_note_table(self) -> None:
        tbl = FacilityRelationshipNote.__table__
        assert "facility_id" in tbl.c
        assert "note_type" in tbl.c
        assert "content" in tbl.c
        assert "created_by_user_id" in tbl.c
        assert "is_internal" in tbl.c

    def test_service_profile_table(self) -> None:
        tbl = FacilityServiceProfile.__table__
        assert "facility_id" in tbl.c
        assert "service_line" in tbl.c
        assert "accepts_ems_transport" in tbl.c
        assert "average_turnaround_minutes" in tbl.c
        assert "is_active" in tbl.c

    def test_friction_flag_table(self) -> None:
        tbl = FacilityFrictionFlag.__table__
        assert "facility_id" in tbl.c
        assert "category" in tbl.c
        assert "title" in tbl.c
        assert "is_active" in tbl.c
        assert "resolved_by_user_id" in tbl.c
        assert "resolution_notes" in tbl.c

    def test_audit_event_table(self) -> None:
        tbl = FacilityAuditEvent.__table__
        assert "facility_id" in tbl.c
        assert "action" in tbl.c
        assert "actor_user_id" in tbl.c
        assert "correlation_id" in tbl.c


# ── Boundary Tests ───────────────────────────────────────────────────────────


class TestFacilityBoundaries:
    """Directive: Facility data must be agency-scoped. No silent overwrites.
    Operational and billing notes must remain distinguishable."""

    def test_facility_tenant_scoped(self) -> None:
        tbl = Facility.__table__
        assert "tenant_id" in tbl.c

    def test_relationship_note_types_distinguishable(self) -> None:
        tbl = FacilityRelationshipNote.__table__
        assert "note_type" in tbl.c
        assert "is_internal" in tbl.c

    def test_audit_event_tracks_actor(self) -> None:
        tbl = FacilityAuditEvent.__table__
        assert "actor_user_id" in tbl.c
        assert "correlation_id" in tbl.c
