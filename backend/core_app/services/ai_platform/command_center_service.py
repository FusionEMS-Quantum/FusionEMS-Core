"""AI Command Center Service — founder dashboard metrics, top actions, health score."""
# pylint: disable=not-callable
from __future__ import annotations

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from core_app.models.ai_platform import (
    AIConfidenceLevel,
    AIOverrideState,
    AIReviewItem,
    AIRiskTier,
    AITenantSettings,
    AIUseCase,
    AIUserFacingSummary,
    AIWorkflowRun,
    AIWorkflowState,
)
from core_app.schemas.ai_platform import (
    AICommandCenterMetrics,
    AIGovernanceAction,
    AIHighRiskRecommendation,
    AIReviewQueueEntry,
    AITenantSettingsUpdate,
    AIUserFacingSummaryCreate,
)
from core_app.schemas.auth import CurrentUser


class AICommandCenterService:

    def __init__(self, db: Session, user: CurrentUser) -> None:
        self._db = db
        self._user = user

    def get_metrics(self) -> AICommandCenterMetrics:
        tid = self._user.tenant_id

        # Tenant AI enabled check
        tenant_settings = (
            self._db.query(AITenantSettings)
            .filter(AITenantSettings.tenant_id == tid)
            .first()
        )
        tenant_ai_enabled = tenant_settings.ai_enabled if tenant_settings else True

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

        # High-risk recommendations awaiting approval (separate widget)
        high_risk_recs = self._get_high_risk_recommendations(tid)

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
            high_risk_recommendations=high_risk_recs,
            tenant_ai_enabled=tenant_ai_enabled,
        )

    def _get_high_risk_recommendations(self, tid: uuid.UUID) -> list[AIHighRiskRecommendation]:
        """Return workflows from HIGH_RISK or RESTRICTED use cases that are pending review."""
        rows = (
            self._db.query(AIWorkflowRun)
            .join(AIUseCase, AIWorkflowRun.use_case_id == AIUseCase.id)
            .filter(
                AIWorkflowRun.tenant_id == tid,
                AIUseCase.risk_tier.in_([AIRiskTier.HIGH_RISK.value, AIRiskTier.RESTRICTED.value]),
                AIWorkflowRun.override_state.in_([
                    AIOverrideState.REVIEW_PENDING.value,
                    AIOverrideState.HUMAN_TAKEOVER.value,
                ]),
            )
            .order_by(AIWorkflowRun.created_at.desc())
            .limit(10)
            .all()
        )
        return [
            AIHighRiskRecommendation(
                workflow_id=r.id,
                use_case_name=r.use_case.name if r.use_case else "Unknown",
                domain=r.use_case.domain if r.use_case else "unknown",
                risk_tier=r.use_case.risk_tier if r.use_case else "UNKNOWN",
                confidence=r.confidence_level,
                explanation_summary=r.explanation_summary,
                override_state=r.override_state,
                created_at=r.created_at,
            )
            for r in rows
        ]

    # ── Tenant Settings ───────────────────────────────────────────────────

    def get_tenant_settings(self) -> AITenantSettings | None:
        return (
            self._db.query(AITenantSettings)
            .filter(AITenantSettings.tenant_id == self._user.tenant_id)
            .first()
        )

    def update_tenant_settings(self, payload: AITenantSettingsUpdate) -> AITenantSettings:
        settings = self.get_tenant_settings()
        if not settings:
            settings = AITenantSettings(tenant_id=self._user.tenant_id)
            self._db.add(settings)
            self._db.flush()

        if payload.ai_enabled is not None:
            settings.ai_enabled = payload.ai_enabled
        if payload.default_risk_tier is not None:
            settings.default_risk_tier = payload.default_risk_tier.value
        if payload.auto_approve_low_risk is not None:
            settings.auto_approve_low_risk = payload.auto_approve_low_risk
        if payload.require_human_review_high_risk is not None:
            settings.require_human_review_high_risk = payload.require_human_review_high_risk
        if payload.max_concurrent_workflows is not None:
            settings.max_concurrent_workflows = payload.max_concurrent_workflows
        if payload.global_confidence_threshold is not None:
            settings.global_confidence_threshold = payload.global_confidence_threshold.value
        if payload.allowed_domains is not None:
            settings.allowed_domains = payload.allowed_domains
        if payload.environment_ai_toggle is not None:
            settings.environment_ai_toggle = payload.environment_ai_toggle

        self._db.commit()
        self._db.refresh(settings)
        return settings

    # ── User-Facing Summaries ─────────────────────────────────────────────

    def create_user_facing_summary(
        self, workflow_id: uuid.UUID, payload: AIUserFacingSummaryCreate
    ) -> AIUserFacingSummary:
        summary = AIUserFacingSummary(
            tenant_id=self._user.tenant_id,
            workflow_id=workflow_id,
            what_happened=payload.what_happened,
            why_it_matters=payload.why_it_matters,
            do_this_next=payload.do_this_next,
            confidence=payload.confidence.value,
            domain=payload.domain,
            is_simple_mode=payload.is_simple_mode,
        )
        self._db.add(summary)
        self._db.commit()
        self._db.refresh(summary)
        return summary

    def get_user_facing_summary(self, workflow_id: uuid.UUID) -> AIUserFacingSummary | None:
        return (
            self._db.query(AIUserFacingSummary)
            .filter(
                AIUserFacingSummary.workflow_id == workflow_id,
                AIUserFacingSummary.tenant_id == self._user.tenant_id,
            )
            .order_by(AIUserFacingSummary.created_at.desc())
            .first()
        )

    # ── Top Actions ───────────────────────────────────────────────────────

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
