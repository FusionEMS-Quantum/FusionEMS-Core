"""Tests for Relationship History domain — Part 6 verification.

Validates timeline event types, warning flags, internal notes,
summary snapshots, and provenance tracking.
"""
from __future__ import annotations

from core_app.models.relationship_history import (
    FacilityWarningFlag,
    InternalAccountNote,
    PatientWarningFlag,
    RelationshipSummarySnapshot,
    RelationshipTimelineEvent,
    TimelineEventType,
    WarningFlagSeverity,
)
from core_app.schemas.relationship_history import (
    FacilityWarningFlagCreate,
    InternalAccountNoteCreate,
    PatientWarningFlagCreate,
    TimelineEventCreate,
    WarningFlagResolve,
)

# ── Event Type Tests ─────────────────────────────────────────────────────────


class TestTimelineEventTypes:
    def test_all_nine_types_defined(self) -> None:
        expected = {
            "PRIOR_TRIP",
            "PRIOR_BALANCE",
            "PRIOR_FACILITY_CONTACT",
            "PRIOR_HANDOFF",
            "PRIOR_DENIAL",
            "PRIOR_PAYMENT_PLAN",
            "PRIOR_COMMUNICATION",
            "INTERNAL_NOTE",
            "WARNING_FLAG",
        }
        actual = {t.value for t in TimelineEventType}
        assert actual == expected


class TestWarningFlagSeverity:
    def test_all_severities_defined(self) -> None:
        expected = {"BLOCKING", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"}
        actual = {s.value for s in WarningFlagSeverity}
        assert actual == expected


# ── Model Table Tests ────────────────────────────────────────────────────────


class TestRelationshipHistoryModels:
    def test_timeline_event_table(self) -> None:
        tbl = RelationshipTimelineEvent.__table__
        assert tbl.name == "relationship_timeline_events"
        assert "patient_id" in tbl.c
        assert "facility_id" in tbl.c
        assert "event_type" in tbl.c
        assert "title" in tbl.c
        assert "description" in tbl.c
        assert "source" in tbl.c
        assert "source_entity_id" in tbl.c
        assert "actor_user_id" in tbl.c

    def test_internal_account_note_table(self) -> None:
        tbl = InternalAccountNote.__table__
        assert tbl.name == "internal_account_notes"
        assert "patient_id" in tbl.c
        assert "note_type" in tbl.c
        assert "content" in tbl.c
        assert "created_by_user_id" in tbl.c
        assert "is_sensitive" in tbl.c
        assert "visibility" in tbl.c

    def test_patient_warning_flag_table(self) -> None:
        tbl = PatientWarningFlag.__table__
        assert tbl.name == "patient_warning_flags"
        assert "patient_id" in tbl.c
        assert "severity" in tbl.c
        assert "flag_type" in tbl.c
        assert "title" in tbl.c
        assert "is_active" in tbl.c
        assert "created_by_user_id" in tbl.c
        assert "resolved_by_user_id" in tbl.c
        assert "resolution_notes" in tbl.c

    def test_facility_warning_flag_table(self) -> None:
        tbl = FacilityWarningFlag.__table__
        assert tbl.name == "facility_warning_flags"
        assert "facility_id" in tbl.c
        assert "severity" in tbl.c

    def test_summary_snapshot_table(self) -> None:
        tbl = RelationshipSummarySnapshot.__table__
        assert tbl.name == "relationship_summary_snapshots"
        assert "patient_id" in tbl.c
        assert "facility_id" in tbl.c
        assert "summary_type" in tbl.c
        assert "content" in tbl.c
        assert "source" in tbl.c
        assert "confidence_score" in tbl.c


# ── Schema Tests ─────────────────────────────────────────────────────────────


class TestRelationshipHistorySchemas:
    def test_timeline_event_create(self) -> None:
        ev = TimelineEventCreate(
            event_type=TimelineEventType.PRIOR_TRIP,
            title="Transport on 2026-01-15",
            description="Patient transported from SNF to hospital",
            source="SYSTEM",
        )
        assert ev.event_type == TimelineEventType.PRIOR_TRIP

    def test_internal_note_create(self) -> None:
        note = InternalAccountNoteCreate(
            note_type="billing",
            content="Patient disputed balance — pending review",
        )
        assert note.note_type == "billing"

    def test_patient_warning_create(self) -> None:
        flag = PatientWarningFlagCreate(
            severity=WarningFlagSeverity.HIGH,
            flag_type="billing_risk",
            title="Multiple denials",
            description="3 consecutive claim denials for this patient",
        )
        assert flag.severity == WarningFlagSeverity.HIGH

    def test_facility_warning_create(self) -> None:
        flag = FacilityWarningFlagCreate(
            severity=WarningFlagSeverity.MEDIUM,
            flag_type="frequent_utilizer",
            title="High transport volume",
            description="Facility sending 20+ transports/week",
        )
        assert flag.flag_type == "frequent_utilizer"

    def test_warning_resolve(self) -> None:
        resolve = WarningFlagResolve(
            resolution_notes="Issue addressed with facility manager",
        )
        assert resolve.resolution_notes is not None


# ── Provenance Tests ─────────────────────────────────────────────────────────


class TestProvenance:
    """Directive: Timeline entries must preserve source and timestamp.
    Internal notes must be permission-controlled."""

    def test_timeline_has_source(self) -> None:
        tbl = RelationshipTimelineEvent.__table__
        assert "source" in tbl.c
        assert "source_entity_id" in tbl.c

    def test_timeline_has_timestamp(self) -> None:
        tbl = RelationshipTimelineEvent.__table__
        assert "created_at" in tbl.c

    def test_internal_note_has_visibility(self) -> None:
        tbl = InternalAccountNote.__table__
        assert "visibility" in tbl.c
        assert "is_sensitive" in tbl.c

    def test_warning_flag_auditable(self) -> None:
        tbl = PatientWarningFlag.__table__
        assert "created_by_user_id" in tbl.c
        assert "resolved_by_user_id" in tbl.c
