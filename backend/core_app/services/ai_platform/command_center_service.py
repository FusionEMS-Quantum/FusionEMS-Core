"""AI Command Center Service — founder dashboard metrics, top actions, health score."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from core_app.models.ai_platform import (
    AIConfidenceLevel,
    AIGovernanceState,
    AIOverrideState,
    AIReviewItem,
    AIRiskTier,
    AIUseCase,
    AIWorkflowRun,
    AIWorkflowState,
)
from core_app.schemas.ai_platform import (
    AICommandCenterMetrics,
    AIGovernanceAction,
    AIReviewQueueEntry,
)
from core_app.schemas.auth import CurrentUser


class AICommandCenterService:

    def __init__(self, db: Session, user: CurrentUser) -> None:
        self._db = db
        self._user = user

    def get_metrics(self) -> AICommandCenterMetrics:
        tid = self._user.tenant_id

        # Use-case counts
        total_uc = self._db.query(func.count(AIUseCase.id)).filter(
            AIUseCase.tenant_id == tid
        ).scalar() or 0
        enabled_uc = self._db.query(func.count(AIUseCase.id)).filter(
            AIUseCase.tenant_id == tid, AIUseCase.is_enabled.is_(True)
        ).scalar() or 0
        disabled_wf = total_uc - enabled_uc

        # Risk tier breakdown
        risk_rows = (
            self._db.query(AIUseCase.risk_tier, func.count(AIUseCase.id))
            .filter(AIUseCase.tenant_id == tid)
            .group_by(AIUseCase.risk_tier)
            .all()
        )
        risk_breakdown: dict[str, int] = {r.value: 0 for r in AIRiskTier}
        for tier, cnt in risk_rows:
            risk_breakdown[tier] = cnt

        # Recent workflow stats (last 200 runs)
        recent_runs = (
            self._db.query(AIWorkflowRun)
            .filter(AIWorkflowRun.tenant_id == tid)
            .order_by(AIWorkflowRun.created_at.desc())
            .limit(200)
            .all()
        )

        failed_count = sum(
            1 for r in recent_runs
            if r.state in (AIWorkflowState.FAILED.value, AIWorkflowState.FALLBACK_USED.value)
        )
        low_conf_count = sum(
            1 for r in recent_runs
            if r.confidence_level == AIConfidenceLevel.LOW.value
        )

        # Health score: 100 minus penalty for failures and low-confidence
        total = len(recent_runs) or 1
        health = max(0.0, 100.0 - ((failed_count / total) * 60) - ((low_conf_count / total) * 20))

        # Review queue
        pending_reviews = (
            self._db.query(AIReviewItem)
            .join(AIWorkflowRun, AIReviewItem.workflow_id == AIWorkflowRun.id)
            .join(AIUseCase, AIWorkflowRun.use_case_id == AIUseCase.id)
            .filter(
                AIReviewItem.tenant_id == tid,
                AIReviewItem.status == AIOverrideState.REVIEW_PENDING.value,
            )
            .order_by(AIReviewItem.created_at.desc())
            .limit(10)
            .all()
        )

        review_entries: list[AIReviewQueueEntry] = []
        for item in pending_reviews:
            wf = item.workflow
            review_entries.append(
                AIReviewQueueEntry(
                    review_id=item.id,
                    workflow_id=wf.id,
                    correlation_id=wf.correlation_id,
                    use_case_name=wf.use_case.name if wf.use_case else "Unknown",
                    domain=wf.use_case.domain if wf.use_case else "unknown",
                    priority=item.priority,
                    summary=wf.explanation_summary,
                    created_at=item.created_at,
                )
            )

        # Top 3 governance actions
        top_actions = self._compute_top_actions(
            disabled_wf, failed_count, low_conf_count, len(pending_reviews)
        )

        return AICommandCenterMetrics(
            health_score=round(health, 1),
            total_use_cases=total_uc,
            enabled_use_cases=enabled_uc,
            disabled_workflows=disabled_wf,
            low_confidence_count=low_conf_count,
            review_queue_count=len(pending_reviews),
            failed_runs_count=failed_count,
            risk_tier_breakdown=risk_breakdown,
            recent_reviews=review_entries,
            top_actions=top_actions,
        )

    def _compute_top_actions(
        self,
        disabled: int,
        failed: int,
        low_conf: int,
        pending: int,
    ) -> list[AIGovernanceAction]:
        actions: list[AIGovernanceAction] = []

        if failed > 0:
            actions.append(
                AIGovernanceAction(
                    action_type="investigate_failures",
                    title="Investigate Failed AI Runs",
                    description=f"{failed} AI runs failed or used fallbacks recently. Review error logs.",
                    severity="RED",
                )
            )
        if pending > 0:
            actions.append(
                AIGovernanceAction(
                    action_type="clear_review_queue",
                    title="Clear Human Review Queue",
                    description=f"{pending} AI outputs awaiting human approval. High-risk items may be stale.",
                    severity="ORANGE",
                )
            )
        if low_conf > 0:
            actions.append(
                AIGovernanceAction(
                    action_type="review_low_confidence",
                    title="Review Low-Confidence Outputs",
                    description=f"{low_conf} outputs marked low-confidence. Consider tuning prompts or model bindings.",
                    severity="YELLOW",
                )
            )
        if disabled > 0:
            actions.append(
                AIGovernanceAction(
                    action_type="review_disabled_workflows",
                    title="Review Disabled Workflows",
                    description=f"{disabled} AI use cases are disabled. Confirm if intentional or stale.",
                    severity="GRAY",
                )
            )

        return actions[:3]
