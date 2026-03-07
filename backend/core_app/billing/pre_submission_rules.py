"""
Pre-Submission Rules Engine
============================
Validates claims BEFORE 837 generation / Office Ally submission.
Every rule returns a typed RuleResult. Blocking rules prevent submission.
Non-blocking rules surface warnings but allow the claim to proceed.

This engine is deterministic — no AI, no ML. Pure rule-based checks.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Optional

from sqlalchemy.orm import Session

from core_app.models.billing import Claim, ClaimIssue, ClaimState

logger = logging.getLogger(__name__)


class RuleSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    severity: RuleSeverity
    passed: bool
    what_is_wrong: str = ""
    why_it_matters: str = ""
    what_to_do_next: str = ""


@dataclass
class PreSubmissionVerdict:
    claim_id: uuid.UUID
    submittable: bool
    results: list[RuleResult] = field(default_factory=list)
    blocking_count: int = 0
    warning_count: int = 0
    checked_at: str = ""


class PreSubmissionRulesEngine:
    """
    Runs all pre-submission rules against a claim and returns a verdict.
    Blocking failures prevent submission. Warnings are logged as ClaimIssues.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def evaluate(self, claim: Claim) -> PreSubmissionVerdict:
        """Run all rules and return composite verdict."""
        results: list[RuleResult] = []

        results.append(self._check_patient_demographics(claim))
        results.append(self._check_payer_info(claim))
        results.append(self._check_icd10_codes(claim))
        results.append(self._check_service_lines(claim))
        results.append(self._check_mileage(claim))
        results.append(self._check_signatures(claim))
        results.append(self._check_state_for_submission(claim))
        results.append(self._check_duplicate_submission(claim))
        results.append(self._check_timely_filing(claim))

        blocking = [r for r in results if not r.passed and r.severity == RuleSeverity.BLOCKING]
        warnings = [r for r in results if not r.passed and r.severity != RuleSeverity.BLOCKING]

        verdict = PreSubmissionVerdict(
            claim_id=claim.id,
            submittable=len(blocking) == 0,
            results=results,
            blocking_count=len(blocking),
            warning_count=len(warnings),
            checked_at=datetime.now(UTC).isoformat(),
        )

        # Persist failed rule results as ClaimIssues for audit
        for r in results:
            if not r.passed:
                self._persist_issue(claim, r)

        logger.info(
            "pre_submission_check claim_id=%s submittable=%s blocking=%d warnings=%d",
            claim.id, verdict.submittable, verdict.blocking_count, verdict.warning_count,
        )
        return verdict

    # ── Individual Rules ──────────────────────────────────────────────────────

    def _check_patient_demographics(self, claim: Claim) -> RuleResult:
        patient_id = claim.patient_id
        if not patient_id:
            return RuleResult(
                rule_id="PATIENT_DEMOGRAPHICS",
                severity=RuleSeverity.BLOCKING,
                passed=False,
                what_is_wrong="No patient linked to claim.",
                why_it_matters="837 requires subscriber/patient demographics in Loop 2010BA/2010CA.",
                what_to_do_next="Link a patient record to this claim before submission.",
            )
        return RuleResult(rule_id="PATIENT_DEMOGRAPHICS", severity=RuleSeverity.BLOCKING, passed=True)

    def _check_payer_info(self, claim: Claim) -> RuleResult:
        if not claim.primary_payer_id or not claim.primary_payer_name:
            return RuleResult(
                rule_id="PAYER_INFO",
                severity=RuleSeverity.BLOCKING,
                passed=False,
                what_is_wrong="Primary payer ID or name is missing.",
                why_it_matters="837 Loop 2010BB requires payer identification for routing.",
                what_to_do_next="Set primary_payer_id and primary_payer_name on the claim.",
            )
        return RuleResult(rule_id="PAYER_INFO", severity=RuleSeverity.BLOCKING, passed=True)

    def _check_icd10_codes(self, claim: Claim) -> RuleResult:
        errors = claim.validation_errors or []
        has_icd10 = not any("icd10" in str(e).lower() for e in errors)
        if not has_icd10:
            return RuleResult(
                rule_id="ICD10_CODES",
                severity=RuleSeverity.BLOCKING,
                passed=False,
                what_is_wrong="ICD-10 diagnosis codes are missing or flagged invalid.",
                why_it_matters="Claims without valid ICD-10 codes are auto-denied by payers.",
                what_to_do_next="Add valid ICD-10 codes from the ePCR clinical assessment.",
            )
        return RuleResult(rule_id="ICD10_CODES", severity=RuleSeverity.BLOCKING, passed=True)

    def _check_service_lines(self, claim: Claim) -> RuleResult:
        if claim.total_billed_cents <= 0:
            return RuleResult(
                rule_id="SERVICE_LINES",
                severity=RuleSeverity.BLOCKING,
                passed=False,
                what_is_wrong="Total billed amount is zero or negative.",
                why_it_matters="An 837 with $0 charges will be rejected by the clearinghouse.",
                what_to_do_next="Add service lines with appropriate HCPCS codes and charges.",
            )
        return RuleResult(rule_id="SERVICE_LINES", severity=RuleSeverity.BLOCKING, passed=True)

    def _check_mileage(self, claim: Claim) -> RuleResult:
        errors = claim.validation_errors or []
        missing_mileage = any("mileage" in str(e).lower() for e in errors)
        if missing_mileage:
            return RuleResult(
                rule_id="MILEAGE",
                severity=RuleSeverity.HIGH,
                passed=False,
                what_is_wrong="Transport mileage is missing.",
                why_it_matters="Ambulance claims require mileage for correct reimbursement (A0425).",
                what_to_do_next="Enter loaded mileage from the ePCR trip record.",
            )
        return RuleResult(rule_id="MILEAGE", severity=RuleSeverity.HIGH, passed=True)

    def _check_signatures(self, claim: Claim) -> RuleResult:
        errors = claim.validation_errors or []
        missing_sig = any("signature" in str(e).lower() for e in errors)
        if missing_sig:
            return RuleResult(
                rule_id="SIGNATURES",
                severity=RuleSeverity.HIGH,
                passed=False,
                what_is_wrong="Required signature(s) are missing.",
                why_it_matters="CMS requires patient/authorized rep signature for ambulance claims.",
                what_to_do_next="Obtain the required signature via the ePCR signature workflow.",
            )
        return RuleResult(rule_id="SIGNATURES", severity=RuleSeverity.HIGH, passed=True)

    def _check_state_for_submission(self, claim: Claim) -> RuleResult:
        allowed = {ClaimState.READY_FOR_SUBMISSION, ClaimState.CORRECTED_CLAIM_PENDING}
        if claim.status not in allowed:
            return RuleResult(
                rule_id="CLAIM_STATE",
                severity=RuleSeverity.BLOCKING,
                passed=False,
                what_is_wrong=f"Claim status is {claim.status}, not READY_FOR_SUBMISSION.",
                why_it_matters="Only reviewed claims may be submitted to the clearinghouse.",
                what_to_do_next="Complete billing review to advance the claim to READY_FOR_SUBMISSION.",
            )
        return RuleResult(rule_id="CLAIM_STATE", severity=RuleSeverity.BLOCKING, passed=True)

    def _check_duplicate_submission(self, claim: Claim) -> RuleResult:
        if claim.status == ClaimState.SUBMITTED:
            return RuleResult(
                rule_id="DUPLICATE_SUBMISSION",
                severity=RuleSeverity.BLOCKING,
                passed=False,
                what_is_wrong="Claim has already been submitted.",
                why_it_matters="Duplicate submissions cause payer rejections and audit flags.",
                what_to_do_next="If resubmission is needed, use the corrected-claim workflow.",
            )
        return RuleResult(rule_id="DUPLICATE_SUBMISSION", severity=RuleSeverity.BLOCKING, passed=True)

    def _check_timely_filing(self, claim: Claim) -> RuleResult:
        if claim.aging_days > 365:
            return RuleResult(
                rule_id="TIMELY_FILING",
                severity=RuleSeverity.HIGH,
                passed=False,
                what_is_wrong=f"Claim is {claim.aging_days} days old — exceeds typical timely filing limits.",
                why_it_matters="Most payers deny claims filed after 365 days from date of service.",
                what_to_do_next="Verify timely filing deadline with the payer and submit immediately if eligible.",
            )
        return RuleResult(rule_id="TIMELY_FILING", severity=RuleSeverity.HIGH, passed=True)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _persist_issue(self, claim: Claim, result: RuleResult) -> None:
        """Store failed rule as a ClaimIssue for audit trail and dashboard visibility."""
        issue = ClaimIssue(
            claim_id=claim.id,
            severity=result.severity.value,
            source="RULE",
            what_is_wrong=result.what_is_wrong,
            why_it_matters=result.why_it_matters,
            what_to_do_next=result.what_to_do_next,
            resolved=False,
        )
        self.db.add(issue)
