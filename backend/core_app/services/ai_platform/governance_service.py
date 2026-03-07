"""AI Safety + Governance Service — guardrails, protected actions, gating decisions."""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.ai_platform import (
    AIGovernanceDecision,
    AIGovernanceState,
    AIGuardrailRule,
    AIPolicyEnforcement,
    AIProtectedAction,
    AIRestrictedOutputEvent,
    AIWorkflowRun,
)
from core_app.schemas.auth import CurrentUser


class AIGovernanceService:

    def __init__(self, db: Session, user: CurrentUser) -> None:
        self._db = db
        self._user = user

    # ── Guardrail Evaluation ──────────────────────────────────────────────────

    def evaluate_guardrails(self, workflow_id: uuid.UUID, domain: str) -> list[AIGovernanceDecision]:
        """Check all active guardrail rules for a domain and record decisions."""
        run = self._get_run(workflow_id)
        rules = (
            self._db.query(AIGuardrailRule)
            .filter(
                AIGuardrailRule.tenant_id == self._user.tenant_id,
                AIGuardrailRule.domain == domain,
                AIGuardrailRule.is_active.is_(True),
            )
            .all()
        )

        decisions: list[AIGovernanceDecision] = []
        for rule in rules:
            decision_state = AIGovernanceState.ALLOWED.value
            reason = f"Rule '{rule.rule_name}' evaluated — no conditions matched."

            if rule.enforcement == AIPolicyEnforcement.BLOCK.value:
                decision_state = AIGovernanceState.BLOCKED.value
                reason = f"BLOCKED by guardrail: {rule.rule_name} — {rule.description}"
            elif rule.enforcement == AIPolicyEnforcement.FLAG.value:
                decision_state = AIGovernanceState.HUMAN_REVIEW_REQUIRED.value
                reason = f"FLAGGED by guardrail: {rule.rule_name} — {rule.description}"

            gd = AIGovernanceDecision(
                tenant_id=self._user.tenant_id,
                workflow_id=run.id,
                rule_id=rule.id,
                decision=decision_state,
                reason=reason,
            )
            self._db.add(gd)
            decisions.append(gd)

            # Escalate workflow governance state to the most restrictive decision
            if decision_state == AIGovernanceState.BLOCKED.value:
                run.governance_state = AIGovernanceState.BLOCKED.value
            elif (
                decision_state == AIGovernanceState.HUMAN_REVIEW_REQUIRED.value
                and run.governance_state != AIGovernanceState.BLOCKED.value
            ):
                run.governance_state = AIGovernanceState.HUMAN_REVIEW_REQUIRED.value

        self._db.commit()
        return decisions

    # ── Protected Action Check ────────────────────────────────────────────────

    def check_protected_action(self, action_name: str) -> AIProtectedAction | None:
        """Check if an action is in the protected actions registry."""
        return (
            self._db.query(AIProtectedAction)
            .filter(
                AIProtectedAction.tenant_id == self._user.tenant_id,
                AIProtectedAction.action_name == action_name,
            )
            .first()
        )

    def is_action_blocked(self, action_name: str) -> bool:
        pa = self.check_protected_action(action_name)
        return pa is not None and pa.requires_human

    # ── Restricted Output Logging ─────────────────────────────────────────────

    def record_restricted_output(
        self,
        workflow_id: uuid.UUID,
        output_class: str,
        redacted_fields: dict,
        reason: str,
    ) -> AIRestrictedOutputEvent:
        evt = AIRestrictedOutputEvent(
            tenant_id=self._user.tenant_id,
            workflow_id=workflow_id,
            output_class=output_class,
            redacted_fields=redacted_fields,
            reason=reason,
        )
        self._db.add(evt)
        self._db.commit()
        self._db.refresh(evt)
        return evt

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_guardrail_rules(self, domain: str | None = None) -> Sequence[AIGuardrailRule]:
        q = self._db.query(AIGuardrailRule).filter(
            AIGuardrailRule.tenant_id == self._user.tenant_id
        )
        if domain:
            q = q.filter(AIGuardrailRule.domain == domain)
        return q.all()

    def list_protected_actions(self, domain: str | None = None) -> Sequence[AIProtectedAction]:
        q = self._db.query(AIProtectedAction).filter(
            AIProtectedAction.tenant_id == self._user.tenant_id
        )
        if domain:
            q = q.filter(AIProtectedAction.domain == domain)
        return q.all()

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
