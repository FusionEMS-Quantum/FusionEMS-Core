"""AI Human Override + Review Service — pause, takeover, approve, reject, resume."""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.ai_platform import (
    AIApprovalEvent,
    AIGovernanceState,
    AIHumanOverrideEvent,
    AIOverrideState,
    AIRejectionEvent,
    AIResumeEvent,
    AIReviewItem,
    AIWorkflowRun,
)
from core_app.schemas.auth import CurrentUser


class AIOverrideService:

    def __init__(self, db: Session, user: CurrentUser) -> None:
        self._db = db
        self._user = user

    # ── Human Override ────────────────────────────────────────────────────────

    def override_workflow(
        self,
        workflow_id: uuid.UUID,
        new_state: AIOverrideState,
        reason: str,
    ) -> AIWorkflowRun:
        run = self._get_run(workflow_id)
        prev = run.override_state

        run.override_state = new_state.value

        # Governance consequence mapping
        if new_state == AIOverrideState.HUMAN_TAKEOVER:
            run.governance_state = AIGovernanceState.LIMITED.value
        elif new_state == AIOverrideState.APPROVED:
            run.governance_state = AIGovernanceState.ALLOWED.value
        elif new_state == AIOverrideState.REJECTED:
            run.governance_state = AIGovernanceState.BLOCKED.value
        elif new_state == AIOverrideState.AI_DISABLED_FOR_RECORD:
            run.governance_state = AIGovernanceState.DISABLED.value

        evt = AIHumanOverrideEvent(
            tenant_id=self._user.tenant_id,
            workflow_id=run.id,
            actor_id=self._user.user_id,
            previous_state=prev,
            new_state=new_state.value,
            reason=reason,
        )
        self._db.add(evt)
        self._db.commit()
        self._db.refresh(run)
        return run

    # ── Resume AI after Human Takeover ────────────────────────────────────────

    def resume_ai(self, workflow_id: uuid.UUID, reason: str) -> AIWorkflowRun:
        run = self._get_run(workflow_id)
        if run.override_state not in (
            AIOverrideState.HUMAN_TAKEOVER.value,
            AIOverrideState.AI_DISABLED_FOR_RECORD.value,
        ):
            raise AppError(
                status_code=400,
                code="AI_RESUME_INVALID",
                message="Cannot resume AI — it is not in a paused/takeover state.",
            )

        run.override_state = AIOverrideState.AI_ACTIVE.value
        run.governance_state = AIGovernanceState.ALLOWED.value

        evt = AIResumeEvent(
            tenant_id=self._user.tenant_id,
            workflow_id=run.id,
            actor_id=self._user.user_id,
            reason=reason,
        )
        self._db.add(evt)
        self._db.commit()
        self._db.refresh(run)
        return run

    # ── Review Queue ──────────────────────────────────────────────────────────

    def list_review_queue(self) -> Sequence[AIReviewItem]:
        return (
            self._db.query(AIReviewItem)
            .filter(
                AIReviewItem.tenant_id == self._user.tenant_id,
                AIReviewItem.status == AIOverrideState.REVIEW_PENDING.value,
            )
            .order_by(AIReviewItem.created_at.desc())
            .all()
        )

    def create_review_item(
        self,
        workflow_id: uuid.UUID,
        review_type: str,
        priority: str = "MEDIUM",
    ) -> AIReviewItem:
        item = AIReviewItem(
            tenant_id=self._user.tenant_id,
            workflow_id=workflow_id,
            review_type=review_type,
            priority=priority,
            status=AIOverrideState.REVIEW_PENDING.value,
        )
        self._db.add(item)
        self._db.commit()
        self._db.refresh(item)
        return item

    def approve_review(self, review_item_id: uuid.UUID, notes: str | None = None) -> AIReviewItem:
        item = self._get_review_item(review_item_id)
        item.status = AIOverrideState.APPROVED.value
        item.resolved_at = datetime.now(UTC)

        evt = AIApprovalEvent(
            tenant_id=self._user.tenant_id,
            review_item_id=item.id,
            actor_id=self._user.user_id,
            notes=notes,
        )
        self._db.add(evt)

        # Also update the workflow's override state
        run = self._get_run(item.workflow_id)
        run.override_state = AIOverrideState.APPROVED.value
        run.governance_state = AIGovernanceState.ALLOWED.value

        self._db.commit()
        self._db.refresh(item)
        return item

    def reject_review(
        self,
        review_item_id: uuid.UUID,
        reason: str,
        regenerate_requested: bool = False,
    ) -> AIReviewItem:
        item = self._get_review_item(review_item_id)
        item.status = AIOverrideState.REJECTED.value
        item.resolved_at = datetime.now(UTC)

        if regenerate_requested:
            item.status = AIOverrideState.REGENERATE_REQUESTED.value

        evt = AIRejectionEvent(
            tenant_id=self._user.tenant_id,
            review_item_id=item.id,
            actor_id=self._user.user_id,
            reason=reason,
            regenerate_requested=regenerate_requested,
        )
        self._db.add(evt)

        run = self._get_run(item.workflow_id)
        run.override_state = AIOverrideState.REJECTED.value
        run.governance_state = AIGovernanceState.BLOCKED.value

        self._db.commit()
        self._db.refresh(item)
        return item

    # ── Internal ──────────────────────────────────────────────────────────────

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

    def _get_review_item(self, review_item_id: uuid.UUID) -> AIReviewItem:
        item = (
            self._db.query(AIReviewItem)
            .filter(
                AIReviewItem.id == review_item_id,
                AIReviewItem.tenant_id == self._user.tenant_id,
            )
            .first()
        )
        if not item:
            raise AppError(
                status_code=404,
                code="AI_REVIEW_ITEM_NOT_FOUND",
                message="AI Review Item not found.",
            )
        return item
