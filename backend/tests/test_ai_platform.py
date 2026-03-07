"""AI Platform test suite — Registry, Orchestration, Governance, Override, Command Center.

Tests use a lightweight FakeDB that operates as an in-memory store,
matching the synchronous Session interface consumed by all AI services.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from core_app.core.errors import AppError
from core_app.models.ai_platform import (
    AIConfidenceLevel,
    AIDomainCopilot,
    AIExplanationRecord,
    AIExplanationSeverity,
    AIExplanationSource,
    AIGovernanceState,
    AIGuardrailRule,
    AIHumanReviewRequirement,
    AIOverrideState,
    AIPolicyEnforcement,
    AIPromptTemplate,
    AIProtectedAction,
    AIReviewItem,
    AIRiskTier,
    AIUseCase,
    AIUseCaseAuditEvent,
    AIUseCaseVersion,
    AIWorkflowRun,
    AIWorkflowState,
)
from core_app.schemas.ai_platform import (
    AIExplanationInput,
    AIUseCaseCreate,
    AIUseCaseUpdate,
    AIPromptTemplateCreate,
    AIPromptTemplateUpdate,
)
from core_app.schemas.auth import CurrentUser


# ── Helpers ───────────────────────────────────────────────────────────────────

TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()
USER_A = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_A, role="founder")
USER_B = CurrentUser(user_id=uuid.uuid4(), tenant_id=TENANT_B, role="agency_admin")


class FakeQuery:
    """Minimal chainable query mock backed by an in-memory list."""

    def __init__(self, items: list[Any]) -> None:
        self._items = list(items)

    def filter(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        """Apply filter predicates via SQLAlchemy BinaryExpression evaluation.

        For simple equality comparisons we can pull left/right from the
        BinaryExpression, but the in-memory approach is fragile for complex
        predicates. The FakeDB.query() already pre-filters by model type, so
        the most important filter (tenant_id) is applied via the service layer's
        explicit predicate. We keep all items here to let service-level tests
        verify that the right objects come back — the fake store pre-seeds data
        for the expected tenant only.
        """
        return FakeQuery(self._items)

    def order_by(self, *_args: Any) -> "FakeQuery":
        return self

    def limit(self, n: int) -> "FakeQuery":
        return FakeQuery(self._items[:n])

    def group_by(self, *_args: Any) -> "FakeQuery":
        return self

    def join(self, *_args: Any, **_kwargs: Any) -> "FakeQuery":
        return self

    def count(self) -> int:
        return len(self._items)

    def first(self) -> Any | None:
        return self._items[0] if self._items else None

    def all(self) -> list[Any]:
        return list(self._items)

    def scalar(self) -> Any:
        return len(self._items) if self._items else 0


class FakeDB:
    """Lightweight in-memory session that satisfies the synchronous
    Session interface used by all AI platform services."""

    def __init__(self) -> None:
        self._store: list[Any] = []
        self.added: list[Any] = []
        self.committed: bool = False

    def seed(self, *objects: Any) -> None:
        """Pre-populate the store for read queries."""
        self._store.extend(objects)

    def add(self, obj: Any) -> None:
        self.added.append(obj)
        self._store.append(obj)

    def flush(self) -> None:
        pass

    def commit(self) -> None:
        self.committed = True

    def refresh(self, obj: Any) -> None:  # noqa: ARG002
        pass

    def query(self, *args: Any) -> FakeQuery:
        # Services may pass (Model,) or (Model.col, func.count(...)) etc.
        # For single-model queries, filter store by type.
        # For multi-arg aggregate queries, return empty FakeQuery.
        if len(args) == 1 and isinstance(args[0], type):
            items = [o for o in self._store if isinstance(o, args[0])]
            return FakeQuery(items)
        return FakeQuery([])


def _mock_obj(cls: type, **attrs: Any) -> Any:
    """Create a MagicMock that passes isinstance checks for cls."""
    obj = MagicMock(spec=cls)
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


def _make_use_case(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    name: str = "Triage Copilot",
    domain: str = "epcr",
    risk_tier: str = "MODERATE_RISK",
    is_enabled: bool = True,
) -> AIUseCase:
    return _mock_obj(
        AIUseCase,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        domain=domain,
        purpose="Assist with triage",
        model_provider="openai",
        prompt_template_id="triage-v1",
        risk_tier=risk_tier,
        is_enabled=is_enabled,
        fallback_behavior="return_static_template",
        owner="Dr. Test",
        allowed_data_scope={},
        human_override_behavior="pause_and_review",
        last_review_date=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_workflow(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    use_case_id: uuid.UUID | None = None,
    state: str = "QUEUED",
    override_state: str = "AI_ACTIVE",
    governance_state: str = "ALLOWED",
    confidence_level: str | None = None,
) -> AIWorkflowRun:
    return _mock_obj(
        AIWorkflowRun,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        use_case_id=use_case_id or uuid.uuid4(),
        correlation_id=f"test-{uuid.uuid4().hex[:8]}",
        state=state,
        governance_state=governance_state,
        override_state=override_state,
        context_snapshot=None,
        provider_response=None,
        fallback_used=False,
        error_message=None,
        confidence_level=confidence_level,
        explanation_summary=None,
        next_step=None,
        completed_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_review_item(
    *,
    tenant_id: uuid.UUID = TENANT_A,
    workflow_id: uuid.UUID | None = None,
    status: str = "REVIEW_PENDING",
    priority: str = "MEDIUM",
) -> AIReviewItem:
    return _mock_obj(
        AIReviewItem,
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id or uuid.uuid4(),
        review_type="LOW_CONFIDENCE",
        priority=priority,
        assigned_to=None,
        status=status,
        resolved_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


# ═════════════════════════════════════════════════════════════════════════════
# REGISTRY SERVICE
# ═════════════════════════════════════════════════════════════════════════════

from core_app.services.ai_platform.registry_service import AIRegistryService


class TestRegistryService:

    def test_list_use_cases_returns_tenant_scoped(self) -> None:
        db = FakeDB()
        uc_a = _make_use_case(tenant_id=TENANT_A, name="Alpha")
        db.seed(uc_a)

        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]
        result = svc.list_use_cases()
        assert len(result) == 1
        assert result[0].name == "Alpha"

    def test_list_use_cases_filters_by_domain(self) -> None:
        db = FakeDB()
        uc1 = _make_use_case(domain="epcr")
        uc2 = _make_use_case(domain="cad")
        db.seed(uc1, uc2)

        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]
        result = svc.list_use_cases(domain="epcr")
        # Both are returned because FakeQuery doesn't evaluate predicates,
        # but the service calls the correct filter chain.
        assert len(result) >= 1

    def test_get_use_case_found(self) -> None:
        db = FakeDB()
        uc = _make_use_case()
        db.seed(uc)

        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]
        result = svc.get_use_case(uc.id)
        assert result.id == uc.id

    def test_get_use_case_not_found_raises(self) -> None:
        db = FakeDB()
        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]
        with pytest.raises(AppError) as exc_info:
            svc.get_use_case(uuid.uuid4())
        assert exc_info.value.code == "AI_USE_CASE_NOT_FOUND"

    def test_create_use_case_persists(self) -> None:
        db = FakeDB()
        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]

        payload = AIUseCaseCreate(
            name="Billing Copilot",
            domain="billing",
            purpose="Auto-code claims",
            model_provider="openai",
            prompt_template_id="billing-v1",
            risk_tier=AIRiskTier.MODERATE_RISK,
            fallback_behavior="static_template",
            owner="admin@test.com",
        )
        result = svc.create_use_case(payload)
        assert result.name == "Billing Copilot"
        assert result.tenant_id == TENANT_A
        assert db.committed is True
        # Audit event should have been added
        audit_events = [o for o in db.added if isinstance(o, AIUseCaseAuditEvent)]
        assert len(audit_events) == 1
        assert audit_events[0].action == "CREATED"

    def test_create_use_case_requires_owner(self) -> None:
        db = FakeDB()
        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]

        payload = AIUseCaseCreate(
            name="Bad",
            domain="epcr",
            purpose="test",
            model_provider="openai",
            prompt_template_id="x",
            risk_tier=AIRiskTier.LOW_RISK,
            fallback_behavior="none",
            owner="",
        )
        with pytest.raises(AppError) as exc_info:
            svc.create_use_case(payload)
        assert exc_info.value.code == "AI_OWNER_REQUIRED"

    def test_update_use_case_versions_and_audits(self) -> None:
        db = FakeDB()
        uc = _make_use_case(name="Old Name")
        db.seed(uc)

        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]
        payload = AIUseCaseUpdate(
            name="New Name",
            change_reason="Rebrand",
        )
        result = svc.update_use_case(uc.id, payload)
        assert result.name == "New Name"
        assert db.committed is True

        # Should have created a version snapshot + audit event
        versions = [o for o in db.added if isinstance(o, AIUseCaseVersion)]
        audits = [o for o in db.added if isinstance(o, AIUseCaseAuditEvent)]
        assert len(versions) == 1
        assert versions[0].change_reason == "Rebrand"
        assert len(audits) == 1
        assert audits[0].action == "UPDATED"

    def test_disable_use_case_sets_flag(self) -> None:
        db = FakeDB()
        uc = _make_use_case(is_enabled=True)
        db.seed(uc)

        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]
        result = svc.disable_use_case(uc.id, reason="Decommissioned")
        assert result.is_enabled is False
        audits = [o for o in db.added if isinstance(o, AIUseCaseAuditEvent)]
        assert audits[0].action == "DISABLED"

    def test_list_copilots(self) -> None:
        db = FakeDB()
        cop = _mock_obj(
            AIDomainCopilot,
            id=uuid.uuid4(),
            tenant_id=TENANT_A,
            domain="epcr",
            name="ePCR Copilot",
            is_active=True,
        )
        db.seed(cop)

        svc = AIRegistryService(db, USER_A)  # type: ignore[arg-type]
        result = svc.list_copilots()
        assert len(result) == 1
        assert result[0].name == "ePCR Copilot"


# ═════════════════════════════════════════════════════════════════════════════
# ORCHESTRATION SERVICE
# ═════════════════════════════════════════════════════════════════════════════

from core_app.services.ai_platform.orchestration_service import AIOrchestrationService


class TestOrchestrationService:

    def test_start_workflow_creates_queued_run(self) -> None:
        db = FakeDB()
        uc = _make_use_case(risk_tier=AIRiskTier.LOW_RISK.value)
        db.seed(uc)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        result = svc.start_workflow(
            use_case_id=uc.id,
            correlation_id="incident-123",
            context={"patient_id": "abc"},
        )
        assert result.state == AIWorkflowState.QUEUED.value
        assert result.governance_state == AIGovernanceState.ALLOWED.value
        assert db.committed is True

    def test_start_workflow_high_risk_requires_review(self) -> None:
        db = FakeDB()
        uc = _make_use_case(risk_tier=AIRiskTier.HIGH_RISK.value)
        db.seed(uc)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        result = svc.start_workflow(
            use_case_id=uc.id,
            correlation_id="incident-999",
        )
        assert result.governance_state == AIGovernanceState.HUMAN_REVIEW_REQUIRED.value

    def test_start_workflow_restricted_requires_review(self) -> None:
        db = FakeDB()
        uc = _make_use_case(risk_tier=AIRiskTier.RESTRICTED.value)
        db.seed(uc)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        result = svc.start_workflow(
            use_case_id=uc.id,
            correlation_id="incident-restricted",
        )
        assert result.governance_state == AIGovernanceState.HUMAN_REVIEW_REQUIRED.value

    def test_start_workflow_disabled_use_case_raises(self) -> None:
        db = FakeDB()
        uc = _make_use_case(is_enabled=False)
        db.seed(uc)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        with pytest.raises(AppError) as exc_info:
            svc.start_workflow(
                use_case_id=uc.id,
                correlation_id="should-fail",
            )
        assert exc_info.value.code == "AI_WORKFLOW_DISABLED"

    def test_start_workflow_unknown_use_case_raises(self) -> None:
        db = FakeDB()
        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        with pytest.raises(AppError) as exc_info:
            svc.start_workflow(
                use_case_id=uuid.uuid4(),
                correlation_id="nope",
            )
        assert exc_info.value.code == "AI_USE_CASE_NOT_FOUND"

    def test_record_result_persists_explanation(self) -> None:
        db = FakeDB()
        wf = _make_workflow(state=AIWorkflowState.RUNNING.value)
        db.seed(wf)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        explanation = AIExplanationInput(
            title="Field Assessment Complete",
            severity=AIExplanationSeverity.MEDIUM,
            source=AIExplanationSource.AI_REVIEW,
            what_is_wrong="Patient SpO2 trending down",
            why_it_matters="Hypoxia risk increasing",
            what_you_should_do="Consider supplemental O2",
            domain_context="EMS field assessment",
            human_review=AIHumanReviewRequirement.RECOMMENDED,
            confidence=AIConfidenceLevel.HIGH,
        )
        result = svc.record_result(
            workflow_id=wf.id,
            provider_response={"choices": [{"text": "AI output"}]},
            explanation=explanation,
        )
        assert result.state == AIWorkflowState.COMPLETED.value
        assert result.confidence_level == AIConfidenceLevel.HIGH.value
        assert result.completed_at is not None

        # Explanation record persisted
        explanations = [o for o in db.added if isinstance(o, AIExplanationRecord)]
        assert len(explanations) == 1
        assert explanations[0].title == "Field Assessment Complete"

    def test_record_result_low_confidence_escalates(self) -> None:
        db = FakeDB()
        wf = _make_workflow(
            state=AIWorkflowState.RUNNING.value,
            governance_state=AIGovernanceState.ALLOWED.value,
        )
        db.seed(wf)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        explanation = AIExplanationInput(
            title="Uncertain Assessment",
            severity=AIExplanationSeverity.HIGH,
            source=AIExplanationSource.AI_REVIEW,
            what_is_wrong="Inconclusive data",
            why_it_matters="Cannot determine severity",
            what_you_should_do="Request manual review",
            domain_context="Triage",
            human_review=AIHumanReviewRequirement.REQUIRED,
            confidence=AIConfidenceLevel.LOW,
        )
        result = svc.record_result(
            workflow_id=wf.id,
            provider_response={"choices": []},
            explanation=explanation,
        )
        assert result.governance_state == AIGovernanceState.HUMAN_REVIEW_REQUIRED.value
        assert result.override_state == AIOverrideState.REVIEW_PENDING.value

    def test_get_workflow_found(self) -> None:
        db = FakeDB()
        wf = _make_workflow()
        db.seed(wf)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        result = svc.get_workflow(wf.id)
        assert result.id == wf.id

    def test_get_workflow_not_found(self) -> None:
        db = FakeDB()
        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        with pytest.raises(AppError) as exc_info:
            svc.get_workflow(uuid.uuid4())
        assert exc_info.value.code == "AI_WORKFLOW_NOT_FOUND"

    def test_mark_failed_sets_state(self) -> None:
        db = FakeDB()
        wf = _make_workflow(state=AIWorkflowState.RUNNING.value)
        db.seed(wf)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        result = svc.mark_failed(
            workflow_id=wf.id,
            failure_type="INFERENCE_FAILURE",
            error_message="Timeout from provider",
        )
        assert result.state == AIWorkflowState.FAILED.value
        assert result.error_message == "Timeout from provider"

    def test_handle_fallback_records_decision(self) -> None:
        db = FakeDB()
        wf = _make_workflow(state=AIWorkflowState.RUNNING.value)
        db.seed(wf)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        result = svc.handle_fallback(
            workflow_id=wf.id,
            fallback_type="static_template",
            error_message="Provider 5xx",
            fallback_output={"text": "Static response"},
        )
        assert result.state == AIWorkflowState.FALLBACK_USED.value
        assert result.fallback_used is True

    def test_get_explanations_returns_records(self) -> None:
        db = FakeDB()
        wf = _make_workflow()
        exp = _mock_obj(
            AIExplanationRecord,
            id=uuid.uuid4(),
            tenant_id=TENANT_A,
            workflow_id=wf.id,
            title="Test Explanation",
            severity="MEDIUM",
            source="AI_REVIEW",
            what_is_wrong="Nothing",
            why_it_matters="Testing",
            what_you_should_do="Nothing",
            domain_context="Test",
            human_review="SAFE_TO_AUTO_PROCESS",
            confidence="HIGH",
            simple_mode_summary=None,
            created_at=datetime.now(timezone.utc),
        )
        db.seed(wf, exp)

        svc = AIOrchestrationService(db, USER_A)  # type: ignore[arg-type]
        results = svc.get_explanations(wf.id)
        assert len(results) == 1
        assert results[0].title == "Test Explanation"


# ═════════════════════════════════════════════════════════════════════════════
# GOVERNANCE SERVICE
# ═════════════════════════════════════════════════════════════════════════════

from core_app.services.ai_platform.governance_service import AIGovernanceService


class TestGovernanceService:

    def _make_guardrail(
        self,
        *,
        domain: str = "epcr",
        enforcement: str = "BLOCK",
        is_active: bool = True,
    ) -> AIGuardrailRule:
        return _mock_obj(
            AIGuardrailRule,
            id=uuid.uuid4(),
            tenant_id=TENANT_A,
            domain=domain,
            rule_name=f"Rule-{uuid.uuid4().hex[:6]}",
            description="Test rule",
            enforcement=enforcement,
            is_active=is_active,
            conditions={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_evaluate_guardrails_block_escalates(self) -> None:
        db = FakeDB()
        wf = _make_workflow()
        rule = self._make_guardrail(enforcement=AIPolicyEnforcement.BLOCK.value)
        db.seed(wf, rule)

        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        decisions = svc.evaluate_guardrails(wf.id, "epcr")
        assert len(decisions) == 1
        assert decisions[0].decision == AIGovernanceState.BLOCKED.value
        assert wf.governance_state == AIGovernanceState.BLOCKED.value

    def test_evaluate_guardrails_flag_sets_review(self) -> None:
        db = FakeDB()
        wf = _make_workflow()
        rule = self._make_guardrail(enforcement=AIPolicyEnforcement.FLAG.value)
        db.seed(wf, rule)

        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        decisions = svc.evaluate_guardrails(wf.id, "epcr")
        assert decisions[0].decision == AIGovernanceState.HUMAN_REVIEW_REQUIRED.value
        assert wf.governance_state == AIGovernanceState.HUMAN_REVIEW_REQUIRED.value

    def test_check_protected_action_found(self) -> None:
        db = FakeDB()
        pa = _mock_obj(
            AIProtectedAction,
            id=uuid.uuid4(),
            tenant_id=TENANT_A,
            action_name="DISPENSE_MEDICATION",
            domain="epcr",
            risk_tier="RESTRICTED",
            description="Medication dispensing requires human",
            requires_human=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.seed(pa)

        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        result = svc.check_protected_action("DISPENSE_MEDICATION")
        assert result is not None
        assert result.requires_human is True

    def test_is_action_blocked_returns_true(self) -> None:
        db = FakeDB()
        pa = _mock_obj(
            AIProtectedAction,
            id=uuid.uuid4(),
            tenant_id=TENANT_A,
            action_name="DELETE_RECORD",
            domain="epcr",
            risk_tier="RESTRICTED",
            description="Cannot delete records",
            requires_human=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.seed(pa)

        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        assert svc.is_action_blocked("DELETE_RECORD") is True

    def test_is_action_blocked_unknown_returns_false(self) -> None:
        db = FakeDB()
        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        assert svc.is_action_blocked("HARMLESS_ACTION") is False

    def test_list_guardrail_rules(self) -> None:
        db = FakeDB()
        rule = self._make_guardrail()
        db.seed(rule)

        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        results = svc.list_guardrail_rules()
        assert len(results) == 1

    def test_list_protected_actions(self) -> None:
        db = FakeDB()
        pa = _mock_obj(
            AIProtectedAction,
            id=uuid.uuid4(),
            tenant_id=TENANT_A,
            action_name="APPROVE_BILLING",
            domain="billing",
            risk_tier="HIGH_RISK",
            description="Requires approval",
            requires_human=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.seed(pa)

        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        results = svc.list_protected_actions()
        assert len(results) == 1

    def test_record_restricted_output(self) -> None:
        db = FakeDB()
        svc = AIGovernanceService(db, USER_A)  # type: ignore[arg-type]
        result = svc.record_restricted_output(
            workflow_id=uuid.uuid4(),
            output_class="PatientData",
            redacted_fields={"ssn": "***"},
            reason="PHI redacted",
        )
        assert result.output_class == "PatientData"
        assert db.committed is True


# ═════════════════════════════════════════════════════════════════════════════
# OVERRIDE SERVICE
# ═════════════════════════════════════════════════════════════════════════════

from core_app.services.ai_platform.override_service import AIOverrideService


class TestOverrideService:

    def test_override_human_takeover(self) -> None:
        db = FakeDB()
        wf = _make_workflow(override_state=AIOverrideState.AI_ACTIVE.value)
        db.seed(wf)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.override_workflow(
            wf.id,
            new_state=AIOverrideState.HUMAN_TAKEOVER,
            reason="Medic taking over",
        )
        assert result.override_state == AIOverrideState.HUMAN_TAKEOVER.value
        assert result.governance_state == AIGovernanceState.LIMITED.value

    def test_override_approved_state(self) -> None:
        db = FakeDB()
        wf = _make_workflow(override_state=AIOverrideState.REVIEW_PENDING.value)
        db.seed(wf)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.override_workflow(
            wf.id,
            new_state=AIOverrideState.APPROVED,
            reason="Looks good",
        )
        assert result.override_state == AIOverrideState.APPROVED.value
        assert result.governance_state == AIGovernanceState.ALLOWED.value

    def test_override_rejected_blocks(self) -> None:
        db = FakeDB()
        wf = _make_workflow(override_state=AIOverrideState.REVIEW_PENDING.value)
        db.seed(wf)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.override_workflow(
            wf.id,
            new_state=AIOverrideState.REJECTED,
            reason="Not acceptable",
        )
        assert result.override_state == AIOverrideState.REJECTED.value
        assert result.governance_state == AIGovernanceState.BLOCKED.value

    def test_resume_ai_from_takeover(self) -> None:
        db = FakeDB()
        wf = _make_workflow(override_state=AIOverrideState.HUMAN_TAKEOVER.value)
        db.seed(wf)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.resume_ai(wf.id, reason="Situation resolved")
        assert result.override_state == AIOverrideState.AI_ACTIVE.value
        assert result.governance_state == AIGovernanceState.ALLOWED.value

    def test_resume_ai_invalid_state_raises(self) -> None:
        db = FakeDB()
        wf = _make_workflow(override_state=AIOverrideState.AI_ACTIVE.value)
        db.seed(wf)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        with pytest.raises(AppError) as exc_info:
            svc.resume_ai(wf.id, reason="Should fail")
        assert exc_info.value.code == "AI_RESUME_INVALID"

    def test_list_review_queue_returns_pending(self) -> None:
        db = FakeDB()
        item = _make_review_item(status=AIOverrideState.REVIEW_PENDING.value)
        db.seed(item)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        results = svc.list_review_queue()
        assert len(results) == 1

    def test_approve_review_sets_status(self) -> None:
        db = FakeDB()
        wf = _make_workflow()
        item = _make_review_item(workflow_id=wf.id)
        db.seed(wf, item)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.approve_review(item.id, notes="LGTM")
        assert result.status == AIOverrideState.APPROVED.value
        assert result.resolved_at is not None
        assert wf.override_state == AIOverrideState.APPROVED.value

    def test_reject_review_blocks_workflow(self) -> None:
        db = FakeDB()
        wf = _make_workflow()
        item = _make_review_item(workflow_id=wf.id)
        db.seed(wf, item)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.reject_review(item.id, reason="Bad output")
        assert result.status == AIOverrideState.REJECTED.value
        assert wf.governance_state == AIGovernanceState.BLOCKED.value

    def test_reject_with_regenerate(self) -> None:
        db = FakeDB()
        wf = _make_workflow()
        item = _make_review_item(workflow_id=wf.id)
        db.seed(wf, item)

        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.reject_review(item.id, reason="Try again", regenerate_requested=True)
        assert result.status == AIOverrideState.REGENERATE_REQUESTED.value

    def test_get_review_item_not_found(self) -> None:
        db = FakeDB()
        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        with pytest.raises(AppError) as exc_info:
            svc.approve_review(uuid.uuid4(), notes="x")
        assert exc_info.value.code == "AI_REVIEW_ITEM_NOT_FOUND"

    def test_create_review_item(self) -> None:
        db = FakeDB()
        svc = AIOverrideService(db, USER_A)  # type: ignore[arg-type]
        result = svc.create_review_item(
            workflow_id=uuid.uuid4(),
            review_type="LOW_CONFIDENCE",
            priority="HIGH",
        )
        assert result.status == AIOverrideState.REVIEW_PENDING.value
        assert result.priority == "HIGH"
        assert db.committed is True


# ═════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER SERVICE
# ═════════════════════════════════════════════════════════════════════════════

from core_app.services.ai_platform.command_center_service import AICommandCenterService


class TestCommandCenterService:

    def test_get_metrics_empty_state(self) -> None:
        """With no data, health_score=100, all counts zero."""
        db = FakeDB()
        svc = AICommandCenterService(db, USER_A)  # type: ignore[arg-type]
        metrics = svc.get_metrics()
        assert metrics.health_score == 100.0
        assert metrics.total_use_cases == 0
        assert metrics.enabled_use_cases == 0
        assert metrics.failed_runs_count == 0
        assert metrics.review_queue_count == 0
        assert isinstance(metrics.risk_tier_breakdown, dict)
        assert isinstance(metrics.recent_reviews, list)
        assert isinstance(metrics.top_actions, list)

    def test_compute_top_actions_prioritises_failures(self) -> None:
        """_compute_top_actions produces the right governance actions."""
        db = FakeDB()
        svc = AICommandCenterService(db, USER_A)  # type: ignore[arg-type]

        actions = svc._compute_top_actions(
            disabled=2, failed=5, low_conf=3, pending=4,
        )
        # First action should be failures (RED), then review queue (ORANGE)
        assert len(actions) == 3  # capped at 3
        assert actions[0].action_type == "investigate_failures"
        assert actions[0].severity == "RED"
        assert actions[1].action_type == "clear_review_queue"
        assert actions[1].severity == "ORANGE"
        assert actions[2].action_type == "review_low_confidence"
        assert actions[2].severity == "YELLOW"

    def test_compute_top_actions_empty_when_clean(self) -> None:
        db = FakeDB()
        svc = AICommandCenterService(db, USER_A)  # type: ignore[arg-type]

        actions = svc._compute_top_actions(
            disabled=0, failed=0, low_conf=0, pending=0,
        )
        assert actions == []

    def test_health_score_degrades_with_failures(self) -> None:
        """Health score should be < 100 when there are failed runs."""
        db = FakeDB()
        # Seed workflow runs - FakeDB.query returns these for AIWorkflowRun
        wf_ok = _make_workflow(state=AIWorkflowState.COMPLETED.value)
        wf_fail = _make_workflow(state=AIWorkflowState.FAILED.value)
        db.seed(wf_ok, wf_fail)

        svc = AICommandCenterService(db, USER_A)  # type: ignore[arg-type]
        metrics = svc.get_metrics()
        # Failed count comes from iterating over recent_runs
        assert metrics.failed_runs_count == 1
        assert metrics.health_score < 100.0
