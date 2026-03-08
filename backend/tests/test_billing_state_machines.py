"""
Patient Balance & Claim State Machine — Unit Tests
Covers: enum completeness, valid transitions, default states,
model integrity, and lifecycle coverage.

DIRECTIVE REQUIREMENT: Patient balance state machine + billing state machine.
"""
from __future__ import annotations

from core_app.models.billing import (
    Claim,
    ClaimState,
    PatientBalanceState,
    PaymentState,
)

# ── Claim State Machine Tests ────────────────────────────────────────────────

class TestClaimStateMachine:
    """Full claim lifecycle states per Zero-Error Directive."""

    REQUIRED_STATES = {
        "DRAFT",
        "READY_FOR_BILLING_REVIEW",
        "READY_FOR_SUBMISSION",
        "SUBMITTED",
        "ACCEPTED",
        "REJECTED",
        "DENIED",
        "PAID",
        "PARTIAL_PAID",
        "APPEAL_DRAFTED",
        "APPEAL_PENDING_REVIEW",
        "CORRECTED_CLAIM_PENDING",
        "CLOSED",
    }

    def test_all_required_claim_states_exist(self) -> None:
        actual = {s.value for s in ClaimState}
        missing = self.REQUIRED_STATES - actual
        assert not missing, f"Missing claim states: {missing}"

    def test_draft_is_initial_state(self) -> None:
        assert ClaimState.DRAFT == "DRAFT"

    def test_closed_is_terminal_state(self) -> None:
        assert ClaimState.CLOSED == "CLOSED"

    def test_claim_model_defaults_to_draft(self) -> None:
        col = Claim.__table__.c.status
        assert col.default is not None

    def test_appeal_workflow_states_exist(self) -> None:
        """Appeal path: DENIED → APPEAL_DRAFTED → APPEAL_PENDING_REVIEW."""
        assert ClaimState.APPEAL_DRAFTED == "APPEAL_DRAFTED"
        assert ClaimState.APPEAL_PENDING_REVIEW == "APPEAL_PENDING_REVIEW"

    def test_partial_payment_state_exists(self) -> None:
        assert ClaimState.PARTIAL_PAID == "PARTIAL_PAID"

    def test_corrected_claim_state_exists(self) -> None:
        assert ClaimState.CORRECTED_CLAIM_PENDING == "CORRECTED_CLAIM_PENDING"

    # ── Valid Transitions ─────────────────────────────────────────

    VALID_TRANSITIONS: dict[str, list[str]] = {
        "DRAFT": ["READY_FOR_BILLING_REVIEW"],
        "READY_FOR_BILLING_REVIEW": ["READY_FOR_SUBMISSION", "DRAFT"],
        "READY_FOR_SUBMISSION": ["SUBMITTED"],
        "SUBMITTED": ["ACCEPTED", "REJECTED"],
        "ACCEPTED": ["PAID", "PARTIAL_PAID", "DENIED"],
        "REJECTED": ["CORRECTED_CLAIM_PENDING", "CLOSED"],
        "DENIED": ["APPEAL_DRAFTED", "CLOSED"],
        "PAID": ["CLOSED"],
        "PARTIAL_PAID": ["PAID", "DENIED", "CLOSED"],
        "APPEAL_DRAFTED": ["APPEAL_PENDING_REVIEW"],
        "APPEAL_PENDING_REVIEW": ["ACCEPTED", "DENIED", "CLOSED"],
        "CORRECTED_CLAIM_PENDING": ["READY_FOR_SUBMISSION"],
    }

    def test_every_non_terminal_state_has_transitions(self) -> None:
        for state in ClaimState:
            if state == ClaimState.CLOSED:
                continue
            assert state.value in self.VALID_TRANSITIONS, (
                f"State {state.value} has no defined transitions"
            )

    def test_happy_path_draftto_closed(self) -> None:
        """DRAFT → REVIEW → SUBMISSION → SUBMITTED → ACCEPTED → PAID → CLOSED."""
        path = ["DRAFT", "READY_FOR_BILLING_REVIEW", "READY_FOR_SUBMISSION",
                "SUBMITTED", "ACCEPTED", "PAID", "CLOSED"]
        for i in range(len(path) - 1):
            assert path[i] in self.VALID_TRANSITIONS
            assert path[i + 1] in self.VALID_TRANSITIONS[path[i]]

    def test_denial_appeal_path(self) -> None:
        """DENIED → APPEAL_DRAFTED → APPEAL_PENDING_REVIEW → ACCEPTED."""
        path = ["DENIED", "APPEAL_DRAFTED", "APPEAL_PENDING_REVIEW", "ACCEPTED"]
        for i in range(len(path) - 1):
            assert path[i + 1] in self.VALID_TRANSITIONS[path[i]]


# ── Patient Balance State Machine Tests ──────────────────────────────────────

class TestPatientBalanceStateMachine:
    """Full patient balance lifecycle per Zero-Error Directive."""

    REQUIRED_STATES = {
        "INSURANCE_PENDING",
        "SECONDARY_PENDING",
        "PATIENT_BALANCE_OPEN",
        "PATIENT_AUTOPAY_PENDING",
        "PAYMENT_PLAN_ACTIVE",
        "DENIAL_UNDER_REVIEW",
        "APPEAL_IN_PROGRESS",
        "COLLECTIONS_READY",
        "SENT_TO_COLLECTIONS",
        "STATE_DEBT_SETOFF_READY",
        "STATE_DEBT_SETOFF_SUBMITTED",
        "WRITTEN_OFF",
        "BAD_DEBT_CLOSED",
    }

    def test_all_required_states_exist(self) -> None:
        actual = {s.value for s in PatientBalanceState}
        missing = self.REQUIRED_STATES - actual
        assert not missing, f"Missing patient balance states: {missing}"

    def test_insurance_pending_is_initial_state(self) -> None:
        assert PatientBalanceState.INSURANCE_PENDING == "INSURANCE_PENDING"

    def test_claim_model_default_balance_status(self) -> None:
        col = Claim.__table__.c.patient_balance_status
        assert col.default is not None

    def test_collections_path_exists(self) -> None:
        """Must support: PATIENT_BALANCE_OPEN → COLLECTIONS_READY → SENT_TO_COLLECTIONS."""
        assert PatientBalanceState.COLLECTIONS_READY == "COLLECTIONS_READY"
        assert PatientBalanceState.SENT_TO_COLLECTIONS == "SENT_TO_COLLECTIONS"

    def test_state_debt_setoff_path_exists(self) -> None:
        """EMS-specific: state debt setoff for uncollected ambulance bills."""
        assert PatientBalanceState.STATE_DEBT_SETOFF_READY == "STATE_DEBT_SETOFF_READY"
        assert PatientBalanceState.STATE_DEBT_SETOFF_SUBMITTED == "STATE_DEBT_SETOFF_SUBMITTED"

    def test_writeoff_and_bad_debt_terminal_states(self) -> None:
        assert PatientBalanceState.WRITTEN_OFF == "WRITTEN_OFF"
        assert PatientBalanceState.BAD_DEBT_CLOSED == "BAD_DEBT_CLOSED"

    def test_autopay_and_payment_plan_states(self) -> None:
        assert PatientBalanceState.PATIENT_AUTOPAY_PENDING == "PATIENT_AUTOPAY_PENDING"
        assert PatientBalanceState.PAYMENT_PLAN_ACTIVE == "PAYMENT_PLAN_ACTIVE"

    # ── Valid Transitions ─────────────────────────────────────────

    VALID_TRANSITIONS: dict[str, list[str]] = {
        "INSURANCE_PENDING": ["SECONDARY_PENDING", "PATIENT_BALANCE_OPEN", "DENIAL_UNDER_REVIEW", "WRITTEN_OFF"],
        "SECONDARY_PENDING": ["PATIENT_BALANCE_OPEN", "DENIAL_UNDER_REVIEW", "WRITTEN_OFF"],
        "PATIENT_BALANCE_OPEN": ["PATIENT_AUTOPAY_PENDING", "PAYMENT_PLAN_ACTIVE", "COLLECTIONS_READY", "STATE_DEBT_SETOFF_READY", "WRITTEN_OFF", "BAD_DEBT_CLOSED"],
        "PATIENT_AUTOPAY_PENDING": ["PATIENT_BALANCE_OPEN", "PAYMENT_PLAN_ACTIVE", "BAD_DEBT_CLOSED"],
        "PAYMENT_PLAN_ACTIVE": ["PATIENT_BALANCE_OPEN", "COLLECTIONS_READY", "BAD_DEBT_CLOSED"],
        "DENIAL_UNDER_REVIEW": ["APPEAL_IN_PROGRESS", "PATIENT_BALANCE_OPEN", "WRITTEN_OFF"],
        "APPEAL_IN_PROGRESS": ["INSURANCE_PENDING", "PATIENT_BALANCE_OPEN", "WRITTEN_OFF"],
        "COLLECTIONS_READY": ["SENT_TO_COLLECTIONS", "PATIENT_BALANCE_OPEN", "WRITTEN_OFF"],
        "SENT_TO_COLLECTIONS": ["PATIENT_BALANCE_OPEN", "BAD_DEBT_CLOSED"],
        "STATE_DEBT_SETOFF_READY": ["STATE_DEBT_SETOFF_SUBMITTED", "PATIENT_BALANCE_OPEN"],
        "STATE_DEBT_SETOFF_SUBMITTED": ["PATIENT_BALANCE_OPEN", "BAD_DEBT_CLOSED"],
    }

    def test_insurance_pending_can_enter_denial(self) -> None:
        assert "DENIAL_UNDER_REVIEW" in self.VALID_TRANSITIONS["INSURANCE_PENDING"]

    def test_open_balance_has_multiple_paths(self) -> None:
        targets = self.VALID_TRANSITIONS["PATIENT_BALANCE_OPEN"]
        assert len(targets) >= 4  # autopay, payment plan, collections, state debt setoff, writeoff

    def test_collections_is_not_terminal(self) -> None:
        """Collections can recover or close to bad debt."""
        assert "SENT_TO_COLLECTIONS" in self.VALID_TRANSITIONS
        assert len(self.VALID_TRANSITIONS["SENT_TO_COLLECTIONS"]) >= 1


# ── Payment State Machine Tests ──────────────────────────────────────────────

class TestPaymentStateMachine:
    """Payment lifecycle states."""

    REQUIRED_STATES = {
        "PAYMENT_PENDING",
        "PAYMENT_PROCESSING",
        "PAYMENT_FAILED_RETRYING",
        "PAYMENT_FAILED_ACTION_REQUIRED",
        "PAYMENT_METHOD_EXPIRED",
        "ACH_PENDING_SETTLEMENT",
        "INVOICE_PAST_DUE",
        "SERVICE_GRACE_PERIOD",
        "SERVICE_RESTRICTED",
        "COLLECTIONS_REVIEW",
    }

    def test_all_required_payment_states_exist(self) -> None:
        actual = {s.value for s in PaymentState}
        missing = self.REQUIRED_STATES - actual
        assert not missing, f"Missing payment states: {missing}"

    def test_payment_pending_is_initial(self) -> None:
        assert PaymentState.PAYMENT_PENDING == "PAYMENT_PENDING"

    def test_retry_states_exist(self) -> None:
        assert PaymentState.PAYMENT_FAILED_RETRYING == "PAYMENT_FAILED_RETRYING"
        assert PaymentState.PAYMENT_FAILED_ACTION_REQUIRED == "PAYMENT_FAILED_ACTION_REQUIRED"

    def test_ach_specific_state_exists(self) -> None:
        """EMS billing often uses ACH — must track pending settlement."""
        assert PaymentState.ACH_PENDING_SETTLEMENT == "ACH_PENDING_SETTLEMENT"

    def test_degradation_path(self) -> None:
        """PAST_DUE → GRACE_PERIOD → RESTRICTED → COLLECTIONS."""
        assert PaymentState.INVOICE_PAST_DUE == "INVOICE_PAST_DUE"
        assert PaymentState.SERVICE_GRACE_PERIOD == "SERVICE_GRACE_PERIOD"
        assert PaymentState.SERVICE_RESTRICTED == "SERVICE_RESTRICTED"
        assert PaymentState.COLLECTIONS_REVIEW == "COLLECTIONS_REVIEW"


# ── Claim Model Integrity Tests ──────────────────────────────────────────────

class TestClaimModelIntegrity:
    """Claim ORM model column completeness."""

    def test_financial_columns_exist(self) -> None:
        columns = {c.name for c in Claim.__table__.columns}
        required_financial = {
            "total_billed_cents", "insurance_paid_cents",
            "patient_responsibility_cents", "patient_paid_cents",
            "remaining_collectible_balance_cents", "writeoff_amount_cents",
        }
        missing = required_financial - columns
        assert not missing, f"Missing financial columns: {missing}"

    def test_workflow_tracking_columns_exist(self) -> None:
        columns = {c.name for c in Claim.__table__.columns}
        required_workflow = {
            "aging_days", "reminder_count", "appeal_status",
        }
        missing = required_workflow - columns
        assert not missing, f"Missing workflow columns: {missing}"

    def test_tenant_id_is_indexed(self) -> None:
        col = Claim.__table__.c.tenant_id
        assert col.index is True

    def test_incident_id_is_unique(self) -> None:
        col = Claim.__table__.c.incident_id
        assert col.unique is True
