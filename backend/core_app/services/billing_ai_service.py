"""
Billing AI Service
===================
Deterministic billing intelligence module.
Provides denial prediction, appeal strategy recommendations,
and billing health scoring.

AI isolation rule: all AI output is advisory. Failures in this module
must never block billing workflows. Every prediction includes confidence
and a deterministic fallback.
"""
# pylint: disable=not-callable
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from core_app.models.billing import (
    Claim,
    ClaimIssue,
    ClaimState,
    PatientBalanceState,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DenialPrediction:
    claim_id: uuid.UUID
    risk_score: float  # 0.0 – 1.0
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    top_risk_factors: list[str]
    recommended_actions: list[str]
    confidence: float
    model_version: str = "rules_v1"


@dataclass(frozen=True)
class AppealStrategy:
    claim_id: uuid.UUID
    denial_code: str
    recommended_strategy: str
    supporting_evidence: list[str]
    estimated_success_pct: float
    confidence: float
    model_version: str = "rules_v1"


@dataclass(frozen=True)
class BillingHealthScore:
    tenant_id: uuid.UUID
    overall_score: int  # 0–100
    grade: str  # A, B, C, D, F
    factors: list[dict[str, Any]]
    recommendations: list[str]
    computed_at: str


class BillingAIService:
    """
    Advisory billing intelligence. All methods are non-fatal:
    failures return safe fallback values instead of raising exceptions.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Denial Prediction ─────────────────────────────────────────────────────

    def predict_denial_risk(self, claim: Claim) -> DenialPrediction:
        """
        Rule-based denial risk scoring. Deterministic fallback for future ML model.
        """
        try:
            return self._compute_denial_risk(claim)
        except Exception as exc:
            logger.error("billing_ai_denial_prediction_failed claim_id=%s error=%s", claim.id, exc)
            return DenialPrediction(
                claim_id=claim.id,
                risk_score=0.5,
                risk_level="MEDIUM",
                top_risk_factors=["AI analysis unavailable — using fallback score"],
                recommended_actions=["Review claim manually before submission"],
                confidence=0.0,
            )

    def _compute_denial_risk(self, claim: Claim) -> DenialPrediction:
        risk = 0.05
        factors: list[str] = []
        actions: list[str] = []

        # Missing payer info
        if not claim.primary_payer_id:
            risk += 0.25
            factors.append("Missing primary payer ID")
            actions.append("Set primary payer before submission")

        # Validation errors present
        if claim.validation_errors:
            error_count = len(claim.validation_errors)
            risk += min(0.3, 0.1 * error_count)
            factors.append(f"{error_count} validation error(s) present")
            actions.append("Resolve all validation errors")

        # $0 billed
        if claim.total_billed_cents <= 0:
            risk += 0.30
            factors.append("Zero-dollar claim")
            actions.append("Add service lines with charges")

        # Aging > 180 days — timely filing risk
        if claim.aging_days > 180:
            risk += 0.15
            factors.append(f"Claim aging {claim.aging_days} days — timely filing risk")
            actions.append("Submit immediately to avoid timely filing denial")

        # Check for unresolved issues
        issue_count = self.db.query(func.count(ClaimIssue.id)).filter(
            ClaimIssue.claim_id == claim.id,
            not ClaimIssue.resolved,
        ).scalar() or 0

        if issue_count > 0:
            risk += min(0.2, 0.05 * issue_count)
            factors.append(f"{issue_count} unresolved issue(s)")
            actions.append("Resolve open claim issues")

        risk = min(round(risk, 2), 0.99)
        level = (
            "CRITICAL" if risk >= 0.7
            else "HIGH" if risk >= 0.5
            else "MEDIUM" if risk >= 0.3
            else "LOW"
        )

        return DenialPrediction(
            claim_id=claim.id,
            risk_score=risk,
            risk_level=level,
            top_risk_factors=factors or ["No significant risk factors detected"],
            recommended_actions=actions or ["Claim appears ready for submission"],
            confidence=0.85,
        )

    # ── Appeal Strategy ───────────────────────────────────────────────────────

    def recommend_appeal_strategy(
        self,
        claim: Claim,
        denial_code: str,
    ) -> AppealStrategy:
        """
        Rule-based appeal strategy recommendation.
        """
        try:
            return self._compute_appeal_strategy(claim, denial_code)
        except Exception as exc:
            logger.error("billing_ai_appeal_strategy_failed claim_id=%s error=%s", claim.id, exc)
            return AppealStrategy(
                claim_id=claim.id,
                denial_code=denial_code,
                recommended_strategy="Manual review required — AI analysis unavailable.",
                supporting_evidence=[],
                estimated_success_pct=0.0,
                confidence=0.0,
            )

    def _compute_appeal_strategy(self, claim: Claim, denial_code: str) -> AppealStrategy:
        code_upper = denial_code.upper().strip()
        strategies = _DENIAL_CODE_STRATEGIES.get(code_upper)

        if strategies:
            return AppealStrategy(
                claim_id=claim.id,
                denial_code=code_upper,
                recommended_strategy=strategies["strategy"],
                supporting_evidence=strategies["evidence"],
                estimated_success_pct=strategies["success_pct"],
                confidence=0.80,
            )

        # Generic fallback
        return AppealStrategy(
            claim_id=claim.id,
            denial_code=code_upper,
            recommended_strategy=(
                "Submit a formal written appeal with supporting clinical documentation, "
                "medical necessity justification, and any missing information."
            ),
            supporting_evidence=[
                "Include complete ePCR/PCR documentation",
                "Attach signed PCS if required",
                "Reference payer-specific appeal procedures",
            ],
            estimated_success_pct=35.0,
            confidence=0.50,
        )

    # ── Billing Health Score ──────────────────────────────────────────────────

    def compute_health_score(self, tenant_id: uuid.UUID) -> BillingHealthScore:
        """
        Composite billing health score (0–100) for a tenant.
        """
        try:
            return self._compute_health(tenant_id)
        except Exception as exc:
            logger.error("billing_ai_health_score_failed tenant_id=%s error=%s", tenant_id, exc)
            return BillingHealthScore(
                tenant_id=tenant_id,
                overall_score=50,
                grade="C",
                factors=[{"name": "computation_error", "score": 0, "weight": 0}],
                recommendations=["Health score computation failed — review manually"],
                computed_at=datetime.now(UTC).isoformat(),
            )

    def _compute_health(self, tenant_id: uuid.UUID) -> BillingHealthScore:
        total = self.db.query(func.count(Claim.id)).filter(Claim.tenant_id == tenant_id).scalar() or 0

        if total == 0:
            return BillingHealthScore(
                tenant_id=tenant_id,
                overall_score=100,
                grade="A",
                factors=[{"name": "no_claims", "note": "No claims to evaluate"}],
                recommendations=[],
                computed_at=datetime.now(UTC).isoformat(),
            )

        paid = self.db.query(func.count(Claim.id)).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.PAID,
        ).scalar() or 0

        denied = self.db.query(func.count(Claim.id)).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.DENIED,
        ).scalar() or 0

        open_patient_bal = self.db.query(func.count(Claim.id)).filter(
            Claim.tenant_id == tenant_id,
            Claim.patient_balance_status == PatientBalanceState.PATIENT_BALANCE_OPEN,
        ).scalar() or 0

        clean_rate = round(paid / total * 100, 1) if total else 0
        denial_rate = round(denied / total * 100, 1) if total else 0
        open_bal_rate = round(open_patient_bal / total * 100, 1) if total else 0

        factors = []
        score = 0.0

        # Clean claim rate (40% weight)
        clean_score = min(clean_rate, 100)
        factors.append({"name": "clean_claim_rate", "value": clean_rate, "score": clean_score, "weight": 40})
        score += clean_score * 0.40

        # Denial rate penalty (30% weight — lower is better)
        denial_score = max(0, 100 - denial_rate * 5)
        factors.append({"name": "denial_rate", "value": denial_rate, "score": denial_score, "weight": 30})
        score += denial_score * 0.30

        # Open balance rate (20% weight — lower is better)
        bal_score = max(0, 100 - open_bal_rate * 3)
        factors.append({"name": "open_balance_rate", "value": open_bal_rate, "score": bal_score, "weight": 20})
        score += bal_score * 0.20

        # Volume factor (10% weight — having claims is good)
        vol_score = min(100, total * 2)
        factors.append({"name": "claim_volume", "value": total, "score": vol_score, "weight": 10})
        score += vol_score * 0.10

        overall = int(min(round(score), 100))
        grade = (
            "A" if overall >= 90
            else "B" if overall >= 80
            else "C" if overall >= 70
            else "D" if overall >= 60
            else "F"
        )

        recommendations: list[str] = []
        if denial_rate > 10:
            recommendations.append("Denial rate exceeds 10% — review top denial codes and implement targeted fixes.")
        if clean_rate < 80:
            recommendations.append("Clean claim rate below 80% — audit pre-submission validation rules.")
        if open_bal_rate > 20:
            recommendations.append("Over 20% of claims have open patient balances — review collections workflow.")

        return BillingHealthScore(
            tenant_id=tenant_id,
            overall_score=overall,
            grade=grade,
            factors=factors,
            recommendations=recommendations,
            computed_at=datetime.now(UTC).isoformat(),
        )


# ── Denial Code Strategy Lookup ──────────────────────────────────────────────

_DENIAL_CODE_STRATEGIES: dict[str, dict[str, Any]] = {
    "CO-4": {
        "strategy": "Submit modifier clarification with supporting documentation showing distinct services.",
        "evidence": [
            "Include operative notes showing separate procedures",
            "Attach modifier documentation (25, 59, XE, XS)",
        ],
        "success_pct": 65.0,
    },
    "CO-16": {
        "strategy": "Provide missing or corrected information as indicated in the denial remarks.",
        "evidence": [
            "Review the 835 remark codes for specific missing data",
            "Resubmit with complete claim data",
        ],
        "success_pct": 70.0,
    },
    "CO-18": {
        "strategy": "Submit appeal with proof of duplicate claim difference or prior claim withdrawal.",
        "evidence": [
            "Show the claims are for different dates of service or services",
            "Include documentation of prior claim adjustment",
        ],
        "success_pct": 55.0,
    },
    "CO-50": {
        "strategy": "Provide medical necessity documentation including PCS and physician certification.",
        "evidence": [
            "Attach completed PCS form (CMS-1763 or payer equivalent)",
            "Include physician order or certification statement",
            "Document why ambulance transport was medically necessary",
        ],
        "success_pct": 60.0,
    },
    "CO-97": {
        "strategy": "Appeal with documentation showing services were not duplicates or were medically necessary.",
        "evidence": [
            "Include clinical documentation for each billed service",
            "Use appropriate modifiers to distinguish services",
        ],
        "success_pct": 50.0,
    },
    "PR-1": {
        "strategy": "Bill patient for deductible amount. No appeal needed — this is patient responsibility.",
        "evidence": [
            "Collect patient payment per the deductible amount on the EOB",
        ],
        "success_pct": 0.0,
    },
    "PR-2": {
        "strategy": "Bill patient for coinsurance amount. No appeal needed — this is patient responsibility.",
        "evidence": [
            "Collect patient payment per the coinsurance amount on the EOB",
        ],
        "success_pct": 0.0,
    },
}
