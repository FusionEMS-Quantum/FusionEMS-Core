"""
Tests for billing directive gap closure:
  - Pre-submission rules engine
  - Billing AI service (denial prediction, appeal strategy, health score)
  - Schema validation
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import MagicMock

from core_app.billing.pre_submission_rules import (
    PreSubmissionRulesEngine,
    RuleSeverity,
)
from core_app.models.billing import Claim, ClaimState, PatientBalanceState
from core_app.services.billing_ai_service import (
    AppealStrategy,
    BillingAIService,
    BillingHealthScore,
    DenialPrediction,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_claim(**overrides) -> MagicMock:
    claim = MagicMock(spec=Claim)
    claim.id = overrides.get("id", uuid.uuid4())
    claim.tenant_id = overrides.get("tenant_id", uuid.uuid4())
    claim.patient_id = overrides.get("patient_id", uuid.uuid4())
    claim.incident_id = overrides.get("incident_id", uuid.uuid4())
    claim.status = overrides.get("status", ClaimState.READY_FOR_SUBMISSION)
    claim.patient_balance_status = overrides.get("patient_balance_status", PatientBalanceState.INSURANCE_PENDING)
    claim.primary_payer_id = overrides.get("primary_payer_id", "OA12345")
    claim.primary_payer_name = overrides.get("primary_payer_name", "Medicare")
    claim.total_billed_cents = overrides.get("total_billed_cents", 50000)
    claim.insurance_paid_cents = overrides.get("insurance_paid_cents", 0)
    claim.patient_responsibility_cents = overrides.get("patient_responsibility_cents", 0)
    claim.patient_paid_cents = overrides.get("patient_paid_cents", 0)
    claim.remaining_collectible_balance_cents = overrides.get("remaining_collectible_balance_cents", 0)
    claim.validation_errors = overrides.get("validation_errors", [])
    claim.aging_days = overrides.get("aging_days", 10)
    claim.is_valid = overrides.get("is_valid", True)
    claim.pickup_address = overrides.get("pickup_address", "123 Main St")
    claim.dropoff_address = overrides.get("dropoff_address", "456 Hospital Ave")
    claim.medical_necessity_narrative = overrides.get("medical_necessity_narrative", "Patient required ambulance transport due to medical condition.")
    return claim


class FakeDB:
    """Minimal DB mock for services."""

    def __init__(self, scalar_val: int = 0) -> None:
        self._scalar_val = scalar_val
        self._added: list = []

    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def scalar(self):
        return self._scalar_val

    def first(self):
        return None

    def all(self):
        return []

    def add(self, obj):
        self._added.append(obj)

    def commit(self):
        pass

    def flush(self):
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# PRE-SUBMISSION RULES ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestPreSubmissionRulesEngine:
    """Tests for the deterministic pre-submission rules engine."""

    def test_clean_claim_passes_all_rules(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim()

        verdict = engine.evaluate(claim)

        assert verdict.submittable is True
        assert verdict.blocking_count == 0
        assert len(verdict.results) == 14  # 14 rules (9 original + 5 CMS)
        assert all(r.passed for r in verdict.results)

    def test_missing_patient_blocks(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(patient_id=None)

        verdict = engine.evaluate(claim)

        assert verdict.submittable is False
        assert verdict.blocking_count >= 1
        failed = [r for r in verdict.results if r.rule_id == "PATIENT_DEMOGRAPHICS"]
        assert len(failed) == 1
        assert not failed[0].passed
        assert failed[0].severity == RuleSeverity.BLOCKING

    def test_missing_payer_blocks(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(primary_payer_id=None, primary_payer_name=None)

        verdict = engine.evaluate(claim)

        assert verdict.submittable is False
        payer_rule = [r for r in verdict.results if r.rule_id == "PAYER_INFO"]
        assert not payer_rule[0].passed

    def test_zero_billed_blocks(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(total_billed_cents=0)

        verdict = engine.evaluate(claim)

        assert verdict.submittable is False
        svc_rule = [r for r in verdict.results if r.rule_id == "SERVICE_LINES"]
        assert not svc_rule[0].passed
        assert svc_rule[0].severity == RuleSeverity.BLOCKING

    def test_wrong_state_blocks(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(status=ClaimState.DRAFT)

        verdict = engine.evaluate(claim)

        assert verdict.submittable is False
        state_rule = [r for r in verdict.results if r.rule_id == "CLAIM_STATE"]
        assert not state_rule[0].passed

    def test_duplicate_submission_blocks(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(status=ClaimState.SUBMITTED)

        verdict = engine.evaluate(claim)

        assert verdict.submittable is False
        dup_rule = [r for r in verdict.results if r.rule_id == "DUPLICATE_SUBMISSION"]
        assert not dup_rule[0].passed

    def test_timely_filing_warning(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(aging_days=400)

        verdict = engine.evaluate(claim)

        filing_rule = [r for r in verdict.results if r.rule_id == "TIMELY_FILING"]
        assert not filing_rule[0].passed
        assert filing_rule[0].severity == RuleSeverity.HIGH

    def test_mileage_warning(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(validation_errors=["missing mileage data"])

        verdict = engine.evaluate(claim)

        mileage_rule = [r for r in verdict.results if r.rule_id == "MILEAGE"]
        assert not mileage_rule[0].passed
        assert mileage_rule[0].severity == RuleSeverity.HIGH

    def test_corrected_claim_state_allowed(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(status=ClaimState.CORRECTED_CLAIM_PENDING)

        verdict = engine.evaluate(claim)

        state_rule = [r for r in verdict.results if r.rule_id == "CLAIM_STATE"]
        assert state_rule[0].passed

    def test_issues_persisted_to_db(self):
        db = FakeDB()
        engine = PreSubmissionRulesEngine(db)
        claim = _mock_claim(total_billed_cents=0, primary_payer_id=None)

        engine.evaluate(claim)

        # Issues should have been added
        assert len(getattr(db, "_added")) >= 2  # noqa: SLF001


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING AI SERVICE TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBillingAIDenialPrediction:
    """Tests for denial risk prediction."""

    def test_clean_claim_low_risk(self):
        db = FakeDB(scalar_val=0)
        ai = BillingAIService(db)
        claim = _mock_claim()

        pred = ai.predict_denial_risk(claim)

        assert isinstance(pred, DenialPrediction)
        assert pred.risk_score <= 0.15
        assert pred.risk_level == "LOW"
        assert pred.confidence > 0

    def test_missing_payer_high_risk(self):
        db = FakeDB(scalar_val=0)
        ai = BillingAIService(db)
        claim = _mock_claim(primary_payer_id=None)

        pred = ai.predict_denial_risk(claim)

        assert pred.risk_score >= 0.25
        assert "Missing primary payer ID" in pred.top_risk_factors

    def test_zero_billed_high_risk(self):
        db = FakeDB(scalar_val=0)
        ai = BillingAIService(db)
        claim = _mock_claim(total_billed_cents=0)

        pred = ai.predict_denial_risk(claim)

        assert pred.risk_score >= 0.30
        assert "Zero-dollar claim" in pred.top_risk_factors

    def test_validation_errors_increase_risk(self):
        db = FakeDB(scalar_val=0)
        ai = BillingAIService(db)
        claim = _mock_claim(validation_errors=["error1", "error2", "error3"])

        pred = ai.predict_denial_risk(claim)

        assert pred.risk_score >= 0.30
        assert "3 validation error(s) present" in pred.top_risk_factors

    def test_aging_increases_risk(self):
        db = FakeDB(scalar_val=0)
        ai = BillingAIService(db)
        claim = _mock_claim(aging_days=200)

        pred = ai.predict_denial_risk(claim)

        assert any("timely filing" in f.lower() for f in pred.top_risk_factors)

    def test_fallback_on_exception(self):
        db = MagicMock()
        db.query.side_effect = Exception("db error")
        ai = BillingAIService(db)
        claim = _mock_claim()

        pred = ai.predict_denial_risk(claim)

        assert pred.risk_score == 0.5
        assert pred.confidence == 0.0


class TestBillingAIAppealStrategy:
    """Tests for appeal strategy recommendation."""

    def test_known_denial_code(self):
        db = FakeDB()
        ai = BillingAIService(db)
        claim = _mock_claim()

        strategy = ai.recommend_appeal_strategy(claim, "CO-50")

        assert isinstance(strategy, AppealStrategy)
        assert strategy.denial_code == "CO-50"
        assert "medical necessity" in strategy.recommended_strategy.lower()
        assert strategy.confidence > 0

    def test_unknown_denial_code_fallback(self):
        db = FakeDB()
        ai = BillingAIService(db)
        claim = _mock_claim()

        strategy = ai.recommend_appeal_strategy(claim, "UNKNOWN-99")

        assert strategy.denial_code == "UNKNOWN-99"
        assert strategy.confidence == 0.50
        assert len(strategy.supporting_evidence) > 0

    def test_patient_responsibility_no_appeal(self):
        db = FakeDB()
        ai = BillingAIService(db)
        claim = _mock_claim()

        strategy = ai.recommend_appeal_strategy(claim, "PR-1")

        assert strategy.estimated_success_pct == 0.0
        assert "deductible" in strategy.recommended_strategy.lower()

    def test_fallback_on_exception(self):
        db = MagicMock()
        ai = BillingAIService(db)
        claim = _mock_claim()
        # Monkeypatch to force error
        setattr(ai, "_compute_appeal_strategy", MagicMock(side_effect=Exception("fail")))  # noqa: SLF001

        strategy = ai.recommend_appeal_strategy(claim, "CO-4")

        assert strategy.confidence == 0.0
        assert "unavailable" in strategy.recommended_strategy.lower()


class TestBillingAIHealthScore:
    """Tests for billing health score computation."""

    def test_empty_tenant_perfect_score(self):
        db = FakeDB(scalar_val=0)
        ai = BillingAIService(db)
        tenant_id = uuid.uuid4()

        score = ai.compute_health_score(tenant_id)

        assert isinstance(score, BillingHealthScore)
        assert score.overall_score == 100
        assert score.grade == "A"

    def test_fallback_on_exception(self):
        db = MagicMock()
        db.query.side_effect = Exception("db error")
        ai = BillingAIService(db)
        tenant_id = uuid.uuid4()

        score = ai.compute_health_score(tenant_id)

        assert score.overall_score == 50
        assert score.grade == "C"
        assert any("failed" in r.lower() for r in score.recommendations)


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMA VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestBillingSchemas:
    """Ensure all Pydantic schemas instantiate correctly."""

    def test_pre_submission_verdict_out(self):
        from core_app.schemas.billing import PreSubmissionVerdictOut, RuleResultOut

        v = PreSubmissionVerdictOut(
            claim_id=uuid.uuid4(),
            submittable=True,
            results=[
                RuleResultOut(rule_id="TEST", severity="LOW", passed=True),
            ],
            blocking_count=0,
            warning_count=0,
            checked_at="2026-03-07T00:00:00Z",
        )
        assert v.submittable is True

    def test_denial_prediction_out(self):
        from core_app.schemas.billing import DenialPredictionOut

        d = DenialPredictionOut(
            claim_id=uuid.uuid4(),
            risk_score=0.3,
            risk_level="MEDIUM",
            top_risk_factors=["test"],
            recommended_actions=["fix"],
            confidence=0.8,
            model_version="rules_v1",
        )
        assert d.risk_level == "MEDIUM"

    def test_appeal_strategy_out(self):
        from core_app.schemas.billing import AppealStrategyOut

        a = AppealStrategyOut(
            claim_id=uuid.uuid4(),
            denial_code="CO-50",
            recommended_strategy="Appeal with PCS",
            supporting_evidence=["doc1"],
            estimated_success_pct=60.0,
            confidence=0.8,
            model_version="rules_v1",
        )
        assert a.denial_code == "CO-50"

    def test_billing_health_score_out(self):
        from core_app.schemas.billing import BillingHealthScoreOut

        h = BillingHealthScoreOut(
            tenant_id=uuid.uuid4(),
            overall_score=85,
            grade="B",
            factors=[],
            recommendations=[],
            computed_at="2026-03-07T00:00:00Z",
        )
        assert h.grade == "B"

    def test_usage_meter_out(self):
        from core_app.schemas.billing import UsageMeterOut

        u = UsageMeterOut(
            id=uuid.uuid4(),
            subscription_item_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            metric_name="transports",
            period_start=datetime(2026, 3, 1),
            period_end=datetime(2026, 3, 31),
            quantity=42,
            reported_to_stripe=False,
        )
        assert u.metric_name == "transports"

    def test_billing_invoice_mirror_out(self):
        from core_app.schemas.billing import BillingInvoiceMirrorOut

        m = BillingInvoiceMirrorOut(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            stripe_invoice_id="inv_test123",
            status="paid",
            amount_due_cents=5000,
            amount_paid_cents=5000,
            currency="usd",
        )
        assert m.status == "paid"

    def test_agency_policy_schemas(self):
        from core_app.schemas.billing import (
            AgencyDebtSetoffPolicyOut,
            AgencyPaymentPlanPolicyOut,
            AgencyWriteoffPolicyOut,
        )

        pp = AgencyPaymentPlanPolicyOut(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            max_installments=12,
            min_installment_cents=2500,
            interest_rate_bps=0,
            auto_enroll_threshold_cents=10000,
            allow_custom_schedules=False,
            grace_period_days=15,
        )
        assert pp.max_installments == 12

        wo = AgencyWriteoffPolicyOut(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            auto_writeoff_threshold_cents=500,
            max_auto_writeoff_cents=5000,
            require_human_approval_above_cents=5000,
            writeoff_aging_days=365,
            bad_debt_category="UNCOLLECTIBLE",
        )
        assert wo.bad_debt_category == "UNCOLLECTIBLE"

        ds = AgencyDebtSetoffPolicyOut(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            enabled=False,
            min_debt_cents=5000,
            min_aging_days=90,
            exclude_payment_plan_active=True,
            exclude_appeal_in_progress=True,
            max_submissions_per_batch=500,
            require_human_review=True,
        )
        assert ds.require_human_review is True

    def test_debt_setoff_batch_out(self):
        from core_app.schemas.billing import DebtSetoffExportBatchOut

        b = DebtSetoffExportBatchOut(
            id=uuid.uuid4(),
            enrollment_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            batch_reference="BATCH-2026-001",
            record_count=50,
            total_amount_cents=250000,
            status="PENDING",
        )
        assert b.record_count == 50

    def test_state_debt_setoff_rule_pack_out(self):
        from core_app.schemas.billing import DebtSetoffRulePackOut

        rp = DebtSetoffRulePackOut(
            id=uuid.uuid4(),
            state_profile_id=uuid.uuid4(),
            notice_required_days=30,
            max_offset_pct=100,
            hardship_exemption_enabled=False,
            appeal_window_days=30,
            eligible_refund_types=["income_tax"],
            submission_format="CSV_STANDARD",
            required_fields=["ssn", "full_name"],
        )
        assert rp.submission_format == "CSV_STANDARD"
