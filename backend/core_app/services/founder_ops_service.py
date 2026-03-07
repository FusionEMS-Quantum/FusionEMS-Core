"""
Founder Operations Dashboard Service — Module 6 of FINAL_BUILD_STATEMENT.

Provides aggregated operational views across deployment, billing, claims,
communications, CrewLink, collections, and debt-setoff domains.

Must always answer:
- What is broken
- What is blocking money
- What is blocking deployment
- What needs attention today
- What is safe to defer
"""
# pylint: disable=not-callable
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core_app.models.agency import (
    AgencyBillingPolicy,
    AgencyPublicSectorProfile,
    AgencyTaxProfile,
)
from core_app.models.billing import (
    Claim,
    ClaimIssue,
    ClaimState,
    CollectionsReview,
    HumanApprovalEvent,
    PatientBalanceState,
    PaymentLinkEvent,
)
from core_app.models.communications import (
    CommunicationChannelStatus,
    CommunicationMessage,
    CommunicationThread,
    CommunicationThreadState,
)
from core_app.models.crewlink import (
    AlertState,
    CrewPagingAlert,
    CrewPagingEscalationEvent,
    CrewPagingRecipient,
)
from core_app.models.deployment import (
    DeploymentRun,
    DeploymentState,
    FailureAudit,
)
from core_app.models.pricing import SubscriptionPlan
from core_app.models.state_debt_setoff import (
    AgencyDebtSetoffEnrollment,
    DebtSetoffExportBatch,
)
from core_app.models.tenant import Tenant


class FounderOpsService:
    """Aggregated operational intelligence for the founder dashboard."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Deployment Issues ──────────────────────────────────────────────

    def get_deployment_issues(self) -> dict[str, Any]:
        """Active deployment failures, retries, and blocked runs."""
        failed = list(self.db.execute(
            select(DeploymentRun).where(DeploymentRun.current_state == DeploymentState.DEPLOYMENT_FAILED)
        ).scalars().all())

        retrying = list(self.db.execute(
            select(DeploymentRun).where(DeploymentRun.current_state == DeploymentState.RETRY_PENDING)
        ).scalars().all())

        recent_failures = list(self.db.execute(
            select(FailureAudit)
            .order_by(FailureAudit.created_at.desc())
            .limit(10)
        ).scalars().all())

        return {
            "failed_deployments": len(failed),
            "retrying_deployments": len(retrying),
            "recent_failures": [
                {
                    "id": str(f.id),
                    "what_is_wrong": getattr(f, "what_is_wrong", "Unknown"),
                    "severity": getattr(f, "severity", "HIGH"),
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in recent_failures
            ],
        }

    # ── Payment Failures ───────────────────────────────────────────────

    def get_payment_failures(self) -> dict[str, Any]:
        """Stripe payment failures, expired methods, past-due invoices."""
        # Count subscriptions with issues
        past_due = self.db.execute(
            select(func.count(SubscriptionPlan.id)).where(
                SubscriptionPlan.status == "past_due"
            )
        ).scalar_one()

        canceled = self.db.execute(
            select(func.count(SubscriptionPlan.id)).where(
                SubscriptionPlan.status == "canceled"
            )
        ).scalar_one()

        # Payment links that expired
        expired_links = self.db.execute(
            select(func.count(PaymentLinkEvent.id)).where(
                PaymentLinkEvent.status == "EXPIRED"
            )
        ).scalar_one()

        # Recent human approval events for payment-related actions
        pending_approvals = self.db.execute(
            select(func.count(HumanApprovalEvent.id)).where(
                HumanApprovalEvent.action_type.in_(["REFUND", "WRITE_OFF", "COLLECTIONS_STOP"])
            )
        ).scalar_one()

        return {
            "past_due_subscriptions": past_due,
            "canceled_subscriptions": canceled,
            "expired_payment_links": expired_links,
            "pending_approval_actions": pending_approvals,
        }

    # ── Claims Pipeline ────────────────────────────────────────────────

    def get_claims_pipeline(self) -> dict[str, Any]:
        """Ready-to-submit, blocked, denied, and appeal claims overview."""
        def _count_state(state: ClaimState) -> int:
            return self.db.execute(
                select(func.count(Claim.id)).where(Claim.status == state)
            ).scalar_one()

        ready = _count_state(ClaimState.READY_FOR_SUBMISSION)
        blocked_review = _count_state(ClaimState.READY_FOR_BILLING_REVIEW)
        submitted = _count_state(ClaimState.SUBMITTED)
        denied = _count_state(ClaimState.DENIED)
        rejected = _count_state(ClaimState.REJECTED)
        appeal_drafted = _count_state(ClaimState.APPEAL_DRAFTED)
        appeal_pending = _count_state(ClaimState.APPEAL_PENDING_REVIEW)
        corrected = _count_state(ClaimState.CORRECTED_CLAIM_PENDING)

        # Blocking issues count
        blocking_issues = self.db.execute(
            select(func.count(ClaimIssue.id)).where(
                ClaimIssue.severity == "BLOCKING",
                ClaimIssue.resolved.is_(False),
            )
        ).scalar_one()

        return {
            "ready_to_submit": ready,
            "blocked_for_review": blocked_review,
            "submitted": submitted,
            "denied": denied,
            "rejected": rejected,
            "appeals_drafted": appeal_drafted,
            "appeals_pending_review": appeal_pending,
            "corrected_claims_pending": corrected,
            "blocking_issues": blocking_issues,
        }

    # ── High-Risk Denials ──────────────────────────────────────────────

    def get_high_risk_denials(self) -> dict[str, Any]:
        """Denied claims with high financial impact and no appeal started."""
        denied_claims = list(self.db.execute(
            select(Claim).where(
                Claim.status == ClaimState.DENIED,
                Claim.total_billed_cents > 50000,  # > $500
            ).order_by(Claim.total_billed_cents.desc()).limit(20)
        ).scalars().all())

        total_denied_value = sum(c.total_billed_cents for c in denied_claims)

        return {
            "high_value_denials": len(denied_claims),
            "total_denied_value_cents": total_denied_value,
            "top_denials": [
                {
                    "id": str(c.id),
                    "total_billed_cents": c.total_billed_cents,
                    "payer": c.primary_payer_name or "Unknown",
                    "aging_days": c.aging_days,
                }
                for c in denied_claims[:5]
            ],
        }

    # ── Patient Balance Review ─────────────────────────────────────────

    def get_patient_balance_review(self) -> dict[str, Any]:
        """Patient balance summary by state across all claims."""
        def _count_balance_state(state: PatientBalanceState) -> int:
            return self.db.execute(
                select(func.count(Claim.id)).where(Claim.patient_balance_status == state)
            ).scalar_one()

        open_balances = _count_balance_state(PatientBalanceState.PATIENT_BALANCE_OPEN)
        autopay_pending = _count_balance_state(PatientBalanceState.PATIENT_AUTOPAY_PENDING)
        payment_plan = _count_balance_state(PatientBalanceState.PAYMENT_PLAN_ACTIVE)
        collections_ready = _count_balance_state(PatientBalanceState.COLLECTIONS_READY)
        sent_to_collections = _count_balance_state(PatientBalanceState.SENT_TO_COLLECTIONS)
        written_off = _count_balance_state(PatientBalanceState.WRITTEN_OFF)

        # Total outstanding patient responsibility
        total_outstanding = self.db.execute(
            select(func.coalesce(func.sum(Claim.remaining_collectible_balance_cents), 0)).where(
                Claim.patient_balance_status.in_([
                    PatientBalanceState.PATIENT_BALANCE_OPEN,
                    PatientBalanceState.PATIENT_AUTOPAY_PENDING,
                    PatientBalanceState.PAYMENT_PLAN_ACTIVE,
                ])
            )
        ).scalar_one()

        return {
            "open_balances": open_balances,
            "autopay_pending": autopay_pending,
            "payment_plan_active": payment_plan,
            "collections_ready": collections_ready,
            "sent_to_collections": sent_to_collections,
            "written_off": written_off,
            "total_outstanding_cents": total_outstanding,
        }

    # ── Collections Review ─────────────────────────────────────────────

    def get_collections_review(self) -> dict[str, Any]:
        """Pending collections reviews and escalation status."""
        pending = self.db.execute(
            select(func.count(CollectionsReview.id)).where(
                CollectionsReview.approved.is_(False),
                CollectionsReview.decision_at.is_(None),
            )
        ).scalar_one()

        approved = self.db.execute(
            select(func.count(CollectionsReview.id)).where(
                CollectionsReview.approved.is_(True),
            )
        ).scalar_one()

        total_claims_at_collections = self.db.execute(
            select(func.count(Claim.id)).where(
                Claim.patient_balance_status.in_([
                    PatientBalanceState.COLLECTIONS_READY,
                    PatientBalanceState.SENT_TO_COLLECTIONS,
                ])
            )
        ).scalar_one()

        return {
            "pending_reviews": pending,
            "approved_for_collections": approved,
            "total_at_collections_stage": total_claims_at_collections,
        }

    # ── Debt-Setoff Review ─────────────────────────────────────────────

    def get_debt_setoff_review(self) -> dict[str, Any]:
        """Debt-setoff enrollment and batch status overview."""
        active_enrollments = self.db.execute(
            select(func.count(AgencyDebtSetoffEnrollment.id)).where(
                AgencyDebtSetoffEnrollment.status == "ACTIVE"
            )
        ).scalar_one()

        pending_batches = self.db.execute(
            select(func.count(DebtSetoffExportBatch.id)).where(
                DebtSetoffExportBatch.status == "PENDING"
            )
        ).scalar_one()

        submitted_batches = self.db.execute(
            select(func.count(DebtSetoffExportBatch.id)).where(
                DebtSetoffExportBatch.status == "SUBMITTED"
            )
        ).scalar_one()

        total_pending_amount = self.db.execute(
            select(func.coalesce(func.sum(DebtSetoffExportBatch.total_amount_cents), 0)).where(
                DebtSetoffExportBatch.status.in_(["PENDING", "SUBMITTED"])
            )
        ).scalar_one()

        claims_at_setoff = self.db.execute(
            select(func.count(Claim.id)).where(
                Claim.patient_balance_status.in_([
                    PatientBalanceState.STATE_DEBT_SETOFF_READY,
                    PatientBalanceState.STATE_DEBT_SETOFF_SUBMITTED,
                ])
            )
        ).scalar_one()

        return {
            "active_enrollments": active_enrollments,
            "pending_batches": pending_batches,
            "submitted_batches": submitted_batches,
            "total_pending_amount_cents": total_pending_amount,
            "claims_at_setoff_stage": claims_at_setoff,
        }

    # ── Tax/Public-Agency Profile Gaps ─────────────────────────────────

    def get_profile_gaps(self) -> dict[str, Any]:
        """Agencies missing tax profiles, public sector profiles, or billing policies."""
        total_tenants = self.db.execute(
            select(func.count(Tenant.id))
        ).scalar_one()

        has_tax_profile = self.db.execute(
            select(func.count(AgencyTaxProfile.tenant_id))
        ).scalar_one()

        has_public_sector = self.db.execute(
            select(func.count(AgencyPublicSectorProfile.tenant_id))
        ).scalar_one()

        has_billing_policy = self.db.execute(
            select(func.count(AgencyBillingPolicy.tenant_id))
        ).scalar_one()

        return {
            "total_tenants": total_tenants,
            "missing_tax_profile": max(total_tenants - has_tax_profile, 0),
            "missing_public_sector_profile": max(total_tenants - has_public_sector, 0),
            "missing_billing_policy": max(total_tenants - has_billing_policy, 0),
        }

    # ── Billing Communications Health ──────────────────────────────────

    def get_comms_health(self) -> dict[str, Any]:
        """Billing communications health across SMS/email/voice channels."""
        channels = list(self.db.execute(
            select(CommunicationChannelStatus)
        ).scalars().all())

        degraded = [c for c in channels if c.status in ("DEGRADED", "DOWN")]

        open_threads = self.db.execute(
            select(func.count(CommunicationThread.id)).where(
                CommunicationThread.status != CommunicationThreadState.CLOSED
            )
        ).scalar_one()

        # Messages sent in last 24h
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        messages_24h = self.db.execute(
            select(func.count(CommunicationMessage.id)).where(
                CommunicationMessage.created_at >= cutoff
            )
        ).scalar_one()

        failed_messages = self.db.execute(
            select(func.count(CommunicationMessage.id)).where(
                CommunicationMessage.status == "FAILED"
            )
        ).scalar_one()

        return {
            "total_channels": len(channels),
            "degraded_channels": len(degraded),
            "degraded_details": [
                {"channel": c.channel, "provider": c.provider, "status": c.status}
                for c in degraded
            ],
            "open_threads": open_threads,
            "messages_last_24h": messages_24h,
            "failed_messages": failed_messages,
        }

    # ── CrewLink Paging Health ─────────────────────────────────────────

    def get_crewlink_health(self) -> dict[str, Any]:
        """CrewLink paging health — active alerts, response times, escalations."""
        active_alerts = self.db.execute(
            select(func.count(CrewPagingAlert.id)).where(
                CrewPagingAlert.status.in_([
                    AlertState.PAGE_CREATED, AlertState.PAGE_SENT,
                    AlertState.ACKNOWLEDGED, AlertState.ESCALATED,
                ])
            )
        ).scalar_one()

        # Recent escalation events (last 24h)
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        escalations_24h = self.db.execute(
            select(func.count(CrewPagingEscalationEvent.id)).where(
                CrewPagingEscalationEvent.triggered_at >= cutoff
            )
        ).scalar_one()

        # Pending (no response) recipients
        no_response = self.db.execute(
            select(func.count(CrewPagingRecipient.id)).where(
                CrewPagingRecipient.status == "SENT",
                CrewPagingRecipient.response_at.is_(None),
            )
        ).scalar_one()

        completed_24h = self.db.execute(
            select(func.count(CrewPagingAlert.id)).where(
                CrewPagingAlert.status == AlertState.CLOSED,
                CrewPagingAlert.created_at >= cutoff,
            )
        ).scalar_one()

        return {
            "active_alerts": active_alerts,
            "escalations_last_24h": escalations_24h,
            "pending_no_response": no_response,
            "completed_last_24h": completed_24h,
        }

    # ── Top 3 Next Actions ─────────────────────────────────────────────

    def get_top_actions(self) -> list[dict[str, Any]]:
        """
        Synthesizes the top 3 most urgent actions across all domains.
        Priority: blocking money > blocking deployment > ops risk > can defer.
        """
        actions: list[dict[str, Any]] = []

        # 1. Check for deployment failures (blocking deployment)
        failed_deps = self.db.execute(
            select(func.count(DeploymentRun.id)).where(DeploymentRun.current_state == DeploymentState.DEPLOYMENT_FAILED)
        ).scalar_one()
        if failed_deps > 0:
            actions.append({
                "domain": "deployment",
                "severity": "critical",
                "action": f"Resolve {failed_deps} failed deployment(s)",
                "reason": "Agencies cannot go live until deployments complete",
                "category": "blocking_deployment",
            })

        # 2. Check for past-due subscriptions (blocking money)
        past_due = self.db.execute(
            select(func.count(SubscriptionPlan.id)).where(SubscriptionPlan.status == "past_due")
        ).scalar_one()
        if past_due > 0:
            actions.append({
                "domain": "payments",
                "severity": "high",
                "action": f"Address {past_due} past-due subscription(s)",
                "reason": "Revenue at risk from failed payment collection",
                "category": "blocking_money",
            })

        # 3. Check for ready-to-submit claims (blocking money)
        ready = self.db.execute(
            select(func.count(Claim.id)).where(Claim.status == ClaimState.READY_FOR_SUBMISSION)
        ).scalar_one()
        if ready > 0:
            actions.append({
                "domain": "billing",
                "severity": "high",
                "action": f"Submit {ready} claim(s) ready for submission",
                "reason": "Claims aging without submission delays revenue",
                "category": "blocking_money",
            })

        # 4. Check for denied claims (blocking money)
        denied = self.db.execute(
            select(func.count(Claim.id)).where(Claim.status == ClaimState.DENIED)
        ).scalar_one()
        if denied > 0:
            actions.append({
                "domain": "billing",
                "severity": "high",
                "action": f"Review {denied} denied claim(s) for appeal",
                "reason": "Denied claims represent lost revenue without action",
                "category": "blocking_money",
            })

        # 5. Check for blocking claim issues
        blocking = self.db.execute(
            select(func.count(ClaimIssue.id)).where(
                ClaimIssue.severity == "BLOCKING", ClaimIssue.resolved.is_(False)
            )
        ).scalar_one()
        if blocking > 0:
            actions.append({
                "domain": "billing",
                "severity": "critical",
                "action": f"Fix {blocking} blocking claim issue(s)",
                "reason": "Claims cannot proceed until blocking issues are resolved",
                "category": "blocking_money",
            })

        # 6. Check for escalated paging alerts (ops risk)
        escalated = self.db.execute(
            select(func.count(CrewPagingAlert.id)).where(
                CrewPagingAlert.status == AlertState.ESCALATED
            )
        ).scalar_one()
        if escalated > 0:
            actions.append({
                "domain": "crewlink",
                "severity": "high",
                "action": f"Review {escalated} escalated paging alert(s)",
                "reason": "Escalated alerts indicate crew response gaps",
                "category": "ops_risk",
            })

        # 7. Check for collections needing review
        pending_collections = self.db.execute(
            select(func.count(CollectionsReview.id)).where(
                CollectionsReview.approved.is_(False),
                CollectionsReview.decision_at.is_(None),
            )
        ).scalar_one()
        if pending_collections > 0:
            actions.append({
                "domain": "collections",
                "severity": "medium",
                "action": f"Review {pending_collections} pending collections decision(s)",
                "reason": "Aging balances need resolution path",
                "category": "needs_review",
            })

        # Sort by priority then return top 3
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        actions.sort(key=lambda a: priority_order.get(a["severity"], 3))
        return actions[:3]

    # ── Full Summary ───────────────────────────────────────────────────

    def get_ops_summary(self) -> dict[str, Any]:
        """
        Complete founder operations summary.
        Answers all Module 6 questions from the directive.
        """
        return {
            "deployment_issues": self.get_deployment_issues(),
            "payment_failures": self.get_payment_failures(),
            "claims_pipeline": self.get_claims_pipeline(),
            "high_risk_denials": self.get_high_risk_denials(),
            "patient_balance_review": self.get_patient_balance_review(),
            "collections_review": self.get_collections_review(),
            "debt_setoff_review": self.get_debt_setoff_review(),
            "profile_gaps": self.get_profile_gaps(),
            "comms_health": self.get_comms_health(),
            "crewlink_health": self.get_crewlink_health(),
            "top_actions": self.get_top_actions(),
            "generated_at": datetime.now(UTC).isoformat(),
        }
