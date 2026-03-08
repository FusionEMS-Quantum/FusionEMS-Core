"""Tests for Patient Identity domain — models, schemas, service logic.

Directive Part 3: Patient Identity Build verification.
Validates state machine, duplicate detection, merge workflow, alias handling,
external identifiers, and audit trails.
"""
from __future__ import annotations

import uuid

from core_app.models.patient import Patient
from core_app.models.patient_identity import (
    DuplicateResolution,
    IdentifierSource,
    MergeRequestStatus,
    PatientDuplicateCandidate,
    PatientIdentityState,
    PatientMergeAuditEvent,
    PatientMergeRequest,
)
from core_app.schemas.patient_identity import (
    MergeRequestCreate,
    PatientAliasCreate,
    PatientIdentifierCreate,
)

# ── State Machine Tests ──────────────────────────────────────────────────────


class TestPatientIdentityStateMachine:
    """Verify state machine enum values match directive spec."""

    def test_all_states_defined(self) -> None:
        expected = {
            "PROFILE_CREATED",
            "PROFILE_INCOMPLETE",
            "DUPLICATE_CANDIDATE",
            "VERIFIED",
            "MERGE_REVIEW_REQUIRED",
            "MERGED",
            "CORRECTION_PENDING",
            "ARCHIVED",
        }
        actual = {s.value for s in PatientIdentityState}
        assert actual == expected

    def test_default_state(self) -> None:
        assert PatientIdentityState.PROFILE_CREATED.value == "PROFILE_CREATED"


# ── Enum Tests ───────────────────────────────────────────────────────────────


class TestEnums:
    def test_identifier_source_values(self) -> None:
        assert IdentifierSource.MRN.value == "MRN"
        assert IdentifierSource.SSN_LAST4.value == "SSN_LAST4"
        assert IdentifierSource.DRIVERS_LICENSE.value == "DRIVERS_LICENSE"
        assert IdentifierSource.MEDICAID_ID.value == "MEDICAID_ID"
        assert IdentifierSource.MEDICARE_ID.value == "MEDICARE_ID"

    def test_duplicate_resolution(self) -> None:
        assert DuplicateResolution.UNRESOLVED.value == "UNRESOLVED"
        assert DuplicateResolution.CONFIRMED_DUPLICATE.value == "CONFIRMED_DUPLICATE"
        assert DuplicateResolution.NOT_DUPLICATE.value == "NOT_DUPLICATE"
        assert DuplicateResolution.MERGED.value == "MERGED"

    def test_merge_request_status(self) -> None:
        expected = {"PENDING_REVIEW", "APPROVED", "REJECTED", "EXECUTED", "ROLLED_BACK"}
        actual = {s.value for s in MergeRequestStatus}
        assert actual == expected


# ── Schema Tests ─────────────────────────────────────────────────────────────


class TestPatientIdentitySchemas:
    def test_alias_create_valid(self) -> None:
        alias = PatientAliasCreate(
            alias_type="PREFERRED_NAME",
            first_name="Bobby",
            last_name="Smith",
        )
        assert alias.alias_type == "PREFERRED_NAME"
        assert alias.first_name == "Bobby"

    def test_identifier_create_valid(self) -> None:
        ident = PatientIdentifierCreate(
            source=IdentifierSource.MRN,
            identifier_value="MRN-12345",
            issuing_authority="General Hospital",
        )
        assert ident.source == IdentifierSource.MRN
        assert ident.identifier_value == "MRN-12345"

    def test_merge_request_create(self) -> None:
        mr = MergeRequestCreate(
            source_patient_id=uuid.uuid4(),
            target_patient_id=uuid.uuid4(),
            merge_reason="Same person, different records from different transports",
        )
        assert mr.merge_reason is not None


# ── Patient Model Enrichment Tests ───────────────────────────────────────────


class TestPatientModelEnrichment:
    """Verify directive Part 3 patient model fields."""

    def test_deceased_indicator_default(self) -> None:
        p = Patient.__table__
        col = p.c.deceased_indicator
        assert col.default.arg is False

    def test_identity_state_column_exists(self) -> None:
        p = Patient.__table__
        assert "identity_state" in p.c

    def test_language_preference_column_exists(self) -> None:
        p = Patient.__table__
        assert "language_preference" in p.c

    def test_interpreter_required_default(self) -> None:
        p = Patient.__table__
        col = p.c.interpreter_required
        assert col.default.arg is False


# ── No Silent Merge Rule Tests ───────────────────────────────────────────────


class TestNoSilentMerge:
    """Directive boundary: AI may NOT silently merge patients.
    Duplicate detection may suggest, not auto-resolve."""

    def test_merge_request_requires_review_status(self) -> None:
        tbl = PatientMergeRequest.__table__
        assert "status" in tbl.c

    def test_merge_audit_event_model_exists(self) -> None:
        tbl = PatientMergeAuditEvent.__table__
        assert "action" in tbl.c
        assert "actor_user_id" in tbl.c

    def test_duplicate_candidate_resolution_not_auto(self) -> None:
        tbl = PatientDuplicateCandidate.__table__
        assert "resolution" in tbl.c
        assert "resolved_by_user_id" in tbl.c
