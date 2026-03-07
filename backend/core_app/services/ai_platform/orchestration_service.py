"""AI Workflow Orchestration Service — routing, execution, fallback, context assembly."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.ai_platform import (
    AIConfidenceLevel,
    AIContextSnapshot,
    AIExplanationRecord,
    AIFallbackDecision,
    AIGovernanceState,
    AIOverrideState,
    AIRiskTier,
    AIUseCase,
    AIWorkflowFailure,
    AIWorkflowRun,
    AIWorkflowState,
)
from core_app.schemas.ai_platform import AIExplanationInput
from core_app.schemas.auth import CurrentUser


class AIOrchestrationService:

    def __init__(self, db: Session, user: CurrentUser) -> None:
        self._db = db
        self._user = user

    # ── Start a Workflow ──────────────────────────────────────────────────────

    def start_workflow(
        self,
        use_case_id: uuid.UUID,
        correlation_id: str,
        context: dict | None = None,
    ) -> AIWorkflowRun:
        uc = (
            self._db.query(AIUseCase)
            .filter(
                AIUseCase.id == use_case_id,
                AIUseCase.tenant_id == self._user.tenant_id,
            )
            .first()
        )
        if not uc:
            raise AppError(status_code=404, code="AI_USE_CASE_NOT_FOUND", message="AI use case not found.")
        if not uc.is_enabled:
            raise AppError(
                status_code=403,
                code="AI_WORKFLOW_DISABLED",
                message="This AI workflow is currently disabled.",
            )

        governance_state = AIGovernanceState.ALLOWED.value
        if uc.risk_tier in (AIRiskTier.HIGH_RISK.value, AIRiskTier.RESTRICTED.value):
            governance_state = AIGovernanceState.HUMAN_REVIEW_REQUIRED.value

        run = AIWorkflowRun(
            tenant_id=self._user.tenant_id,
            use_case_id=uc.id,
            correlation_id=correlation_id,
            state=AIWorkflowState.QUEUED.value,
            governance_state=governance_state,
            override_state=AIOverrideState.AI_ACTIVE.value,
            context_snapshot=context,
        )
        self._db.add(run)
        self._db.flush()

        # Persist context snapshot for provenance
        if context:
            snap = AIContextSnapshot(
                tenant_id=self._user.tenant_id,
                workflow_id=run.id,
                context_type="initial",
                context_data=context,
                data_scope_hash=hashlib.sha256(
                    json.dumps(context, sort_keys=True, default=str).encode()
                ).hexdigest(),
            )
            self._db.add(snap)

        self._db.commit()
        self._db.refresh(run)
        return run

    # ── Mark Running ──────────────────────────────────────────────────────────

    def mark_running(self, workflow_id: uuid.UUID) -> AIWorkflowRun:
        run = self._get_run(workflow_id)
        run.state = AIWorkflowState.RUNNING.value
        self._db.commit()
        self._db.refresh(run)
        return run

    # ── Record Inference Result ───────────────────────────────────────────────

    def record_result(
        self,
        workflow_id: uuid.UUID,
        provider_response: dict,
        explanation: AIExplanationInput,
    ) -> AIWorkflowRun:
        run = self._get_run(workflow_id)

        run.provider_response = provider_response
        run.state = AIWorkflowState.COMPLETED.value
        run.completed_at = datetime.now(timezone.utc)
        run.confidence_level = explanation.confidence.value
        run.explanation_summary = (
            f"{explanation.why_it_matters}\n\n{explanation.what_is_wrong}"
        )
        run.next_step = explanation.what_you_should_do

        # Persist structured explanation
        rec = AIExplanationRecord(
            tenant_id=self._user.tenant_id,
            workflow_id=run.id,
            title=explanation.title,
            severity=explanation.severity.value,
            source=explanation.source.value,
            what_is_wrong=explanation.what_is_wrong,
            why_it_matters=explanation.why_it_matters,
            what_you_should_do=explanation.what_you_should_do,
            domain_context=explanation.domain_context,
            human_review=explanation.human_review.value,
            confidence=explanation.confidence.value,
            simple_mode_summary=explanation.simple_mode_summary,
        )
        self._db.add(rec)

        # Low-confidence auto-escalation
        if (
            explanation.confidence == AIConfidenceLevel.LOW
            and run.governance_state == AIGovernanceState.ALLOWED.value
        ):
            run.governance_state = AIGovernanceState.HUMAN_REVIEW_REQUIRED.value
            run.override_state = AIOverrideState.REVIEW_PENDING.value

        self._db.commit()
        self._db.refresh(run)
        return run

    # ── Fallback ──────────────────────────────────────────────────────────────

    def handle_fallback(
        self,
        workflow_id: uuid.UUID,
        fallback_type: str,
        error_message: str,
        fallback_output: dict | None = None,
    ) -> AIWorkflowRun:
        run = self._get_run(workflow_id)
        run.state = AIWorkflowState.FALLBACK_USED.value
        run.fallback_used = True
        run.error_message = error_message
        run.completed_at = datetime.now(timezone.utc)

        failure = AIWorkflowFailure(
            tenant_id=self._user.tenant_id,
            workflow_id=run.id,
            failure_type="INFERENCE_FAILURE",
            error_message=error_message,
        )
        self._db.add(failure)

        decision = AIFallbackDecision(
            tenant_id=self._user.tenant_id,
            workflow_id=run.id,
            fallback_type=fallback_type,
            original_error=error_message,
            fallback_output=fallback_output,
        )
        self._db.add(decision)

        self._db.commit()
        self._db.refresh(run)
        return run

    # ── Failure ───────────────────────────────────────────────────────────────

    def mark_failed(
        self,
        workflow_id: uuid.UUID,
        failure_type: str,
        error_message: str,
        error_code: str | None = None,
        provider_metadata: dict | None = None,
    ) -> AIWorkflowRun:
        run = self._get_run(workflow_id)
        run.state = AIWorkflowState.FAILED.value
        run.error_message = error_message
        run.completed_at = datetime.now(timezone.utc)

        failure = AIWorkflowFailure(
            tenant_id=self._user.tenant_id,
            workflow_id=run.id,
            failure_type=failure_type,
            error_code=error_code,
            error_message=error_message,
            provider_metadata=provider_metadata,
        )
        self._db.add(failure)
        self._db.commit()
        self._db.refresh(run)
        return run

    # ── Get a Workflow ────────────────────────────────────────────────────────

    def get_workflow(self, workflow_id: uuid.UUID) -> AIWorkflowRun:
        return self._get_run(workflow_id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get_run(self, workflow_id: uuid.UUID) -> AIWorkflowRun:
        run = (
            self._db.query(AIWorkflowRun)
            .filter(
                AIWorkflowRun.id == workflow_id,
                AIWorkflowRun.tenant_id == self._user.tenant_id,
            )
            .first()
        )
        if not run:
            raise AppError(
                status_code=404,
                code="AI_WORKFLOW_NOT_FOUND",
                message="AI Workflow Run not found.",
            )
        return run
