# pylint: disable=not-callable
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, desc, func
from sqlalchemy.orm import Session

from core_app.models.billing import (
    AppealReview,
    Claim,
    ClaimAuditEvent,
    ClaimIssue,
    ClaimState,
    PaymentLinkEvent,
)
from core_app.models.pricing import Price, SubscriptionItem, SubscriptionPlan
from core_app.models.tenant import Tenant


class BillingCommandService:
    """
    Production service for the Founder Billing Command Center.
    Replaces schemaless mock repos with fully-typed SQLAlchemy access.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_metrics(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        result = self.db.query(
            func.count(Claim.id).label("total_claims"),
            func.sum(case((Claim.status == ClaimState.PAID, 1), else_=0)).label("paid_claims"),
            func.sum(case((Claim.status == ClaimState.DENIED, 1), else_=0)).label("denied_claims"),
            func.sum(case((Claim.status.in_([ClaimState.SUBMITTED, ClaimState.READY_FOR_SUBMISSION]), 1), else_=0)).label("pending_claims"),
            func.sum(case((Claim.status == ClaimState.PAID, Claim.insurance_paid_cents), else_=0)).label("revenue_cents")
        ).filter(Claim.tenant_id == tenant_id).first()

        total = result.total_claims or 0
        paid = result.paid_claims or 0
        denied = result.denied_claims or 0

        return {
            "total_claims": total,
            "paid_claims": paid,
            "denied_claims": denied,
            "pending_claims": result.pending_claims or 0,
            "revenue_cents": result.revenue_cents or 0,
            "clean_claim_rate_pct": round((paid / total * 100) if total > 0 else 0, 2),
            "denial_rate_pct": round((denied / total * 100) if total > 0 else 0, 2),
            "as_of": datetime.now(UTC).isoformat()
        }

    def get_denial_heatmap(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        issues = self.db.query(
            ClaimIssue.what_is_wrong,
            func.count(ClaimIssue.id).label("count")
        ).join(Claim, ClaimIssue.claim_id == Claim.id).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.DENIED,
            not ClaimIssue.resolved
        ).group_by(ClaimIssue.what_is_wrong).order_by(func.count(ClaimIssue.id).desc()).all()

        total_denials = sum(iss.count for iss in issues) if issues else 0
        heatmap = [{"reason_code": iss.what_is_wrong, "count": iss.count} for iss in issues]

        return {
            "heatmap": heatmap,
            "total_denials": total_denials,
            "top_reason": heatmap[0]["reason_code"] if heatmap else None
        }

    def get_payer_performance(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        results = self.db.query(
            Claim.primary_payer_name,
            func.count(Claim.id).label("total_claims"),
            func.sum(case((Claim.status == ClaimState.PAID, 1), else_=0)).label("paid"),
            func.sum(case((Claim.status == ClaimState.DENIED, 1), else_=0)).label("denied"),
            func.sum(case((Claim.status == ClaimState.PAID, Claim.insurance_paid_cents), else_=0)).label("revenue_cents")
        ).filter(
            Claim.tenant_id == tenant_id,
            Claim.primary_payer_name.isnot(None)
        ).group_by(Claim.primary_payer_name).order_by(func.sum(Claim.insurance_paid_cents).desc()).all()

        payers = []
        for r in results:
            clean_pct = round((r.paid / r.total_claims * 100) if r.total_claims > 0 else 0, 2)
            payers.append({
                "payer": r.primary_payer_name,
                "total_claims": r.total_claims,
                "paid": r.paid,
                "denied": r.denied,
                "revenue_cents": r.revenue_cents or 0,
                "clean_claim_rate_pct": clean_pct,
                "avg_days_to_payment": None,
            })

        return {"payers": payers}

    def get_executive_summary(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        total_claims = self.db.query(func.count(Claim.id)).filter(Claim.tenant_id == tenant_id).scalar() or 0
        claim_rev = self.db.query(func.sum(Claim.insurance_paid_cents)).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.PAID
        ).scalar() or 0

        active_plan_ids = [
            plan_id
            for (plan_id,) in self.db.query(SubscriptionPlan.id).filter(
                SubscriptionPlan.tenant_id == tenant_id,
                SubscriptionPlan.status == "active",
            ).all()
        ]

        mrr_cents = 0
        if active_plan_ids:
            items = self.db.query(
                SubscriptionItem, Price
            ).join(Price, SubscriptionItem.price_id == Price.id).filter(
                SubscriptionItem.plan_id.in_(active_plan_ids),
                Price.interval == "month",
            ).all()
            mrr_cents = sum(
                int(price.amount_cents or 0) * int(item.quantity or 1)
                for item, price in items
            )

        return {
            "total_claims": total_claims,
            "total_revenue_cents": claim_rev,
            "mrr_cents": mrr_cents,
            "arr_cents": mrr_cents * 12
        }

    def get_revenue_leakage(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        # Revenue leakage = unresolved denials, missing secondary, open patient balances that are aging
        leakage_items = []
        # Find unappealed denials
        unappealed = self.db.query(Claim).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.DENIED,
            Claim.appeal_status is None
        ).limit(50).all()

        total_leakage_cents = 0
        for c in unappealed:
            total_leakage_cents += c.total_billed_cents
            leakage_items.append({
                "claim_id": c.id,
                "payer": c.primary_payer_name,
                "amount_cents": c.total_billed_cents,
                "denial_reason": "Unappealed Denial",
                "leakage_type": "unappealed_denial"
            })

        return {
            "total_leakage_cents": total_leakage_cents,
            "leakage_items": leakage_items,
            "item_count": len(leakage_items)
        }

    def get_billing_kpis(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        metrics = self.get_dashboard_metrics(tenant_id)
        return {
            "total_claims": metrics["total_claims"],
            "clean_claim_rate": metrics["clean_claim_rate_pct"],
            "denial_rate": metrics["denial_rate_pct"],
            "total_revenue_cents": metrics["revenue_cents"],
            "avg_days_to_payment": None,
            "as_of": metrics["as_of"],
        }

    def get_billing_health(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        metrics = self.get_dashboard_metrics(tenant_id)
        clean_rate = metrics["clean_claim_rate_pct"]
        score = min(100, clean_rate)
        status = (
            "excellent"
            if score >= 90
            else ("good" if score >= 75 else ("fair" if score >= 60 else "poor"))
        )
        return {
            "health_score": score,
            "status": status,
            "clean_claim_rate_pct": clean_rate,
            "total_claims": metrics["total_claims"],
            "as_of": metrics["as_of"],
        }

    def get_ar_concentration_risk(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        open_claims = self.db.query(Claim).filter(
            Claim.tenant_id == tenant_id,
            Claim.status.in_(
                [ClaimState.READY_FOR_SUBMISSION, ClaimState.SUBMITTED, ClaimState.DENIED]
            ),
        ).all()
        payer_ar: dict[str, int] = {}
        total_ar = 0
        for claim in open_claims:
            payer = claim.primary_payer_name or "UNKNOWN"
            amount = int(claim.total_billed_cents or 0)
            payer_ar[payer] = payer_ar.get(payer, 0) + amount
            total_ar += amount
        concentration = []
        for payer, amount in payer_ar.items():
            pct = round(amount / total_ar * 100, 2) if total_ar else 0
            risk = "high" if pct > 40 else ("medium" if pct > 20 else "low")
            concentration.append({"payer": payer, "ar_cents": amount, "pct": pct, "risk": risk})
        concentration.sort(key=lambda x: x["ar_cents"], reverse=True)
        return {"concentration": concentration, "total_ar_cents": total_ar}

    def get_claim_throughput(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        rows = self.db.query(
            func.date(Claim.created_at).label("created_day"),
            func.count(Claim.id).label("count"),
        ).filter(
            Claim.tenant_id == tenant_id
        ).group_by(
            func.date(Claim.created_at)
        ).order_by(
            func.date(Claim.created_at)
        ).all()
        throughput = [{"date": str(r.created_day), "count": int(r.count)} for r in rows]
        avg_daily = round(sum(x["count"] for x in throughput) / max(len(throughput), 1), 1)
        return {"throughput_by_day": throughput, "avg_daily": avg_daily}

    def get_claim_lifecycle(self, tenant_id: uuid.UUID, claim_id: uuid.UUID) -> dict[str, Any] | None:
        claim = self.db.query(Claim).filter(
            Claim.tenant_id == tenant_id, Claim.id == claim_id
        ).first()
        if not claim:
            return None
        events = self.db.query(ClaimAuditEvent).filter(
            ClaimAuditEvent.claim_id == claim_id
        ).order_by(ClaimAuditEvent.created_at.asc()).all()
        return {
            "claim": {
                "id": str(claim.id),
                "tenant_id": str(claim.tenant_id),
                "incident_id": str(claim.incident_id),
                "patient_id": str(claim.patient_id),
                "status": str(claim.status),
                "total_billed_cents": int(claim.total_billed_cents or 0),
                "insurance_paid_cents": int(claim.insurance_paid_cents or 0),
                "created_at": claim.created_at.isoformat(),
                "updated_at": claim.updated_at.isoformat(),
            },
            "lifecycle_events": [
                {
                    "id": str(e.id),
                    "event_type": e.event_type,
                    "old_value": e.old_value,
                    "new_value": e.new_value,
                    "metadata_blob": e.metadata_blob,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ],
        }

    def get_appeal_success(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        results = self.db.query(
            AppealReview.status,
            func.count(AppealReview.id).label("count"),
        ).join(Claim, AppealReview.claim_id == Claim.id).filter(
            Claim.tenant_id == tenant_id
        ).group_by(AppealReview.status).all()

        total = 0
        successful = 0
        for row in results:
            total += int(row.count)
            if row.status in ("APPROVED_FOR_SUBMISSION", "approved", "paid"):
                successful += int(row.count)
        return {
            "total_appeals": total,
            "successful": successful,
            "success_rate_pct": round(successful / total * 100, 2) if total > 0 else 0,
        }

    def get_fraud_anomaly(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        rows = self.db.query(
            Claim.patient_id,
            func.count(Claim.id).label("claim_count"),
        ).filter(
            Claim.tenant_id == tenant_id
        ).group_by(Claim.patient_id).having(func.count(Claim.id) > 10).all()

        anomalies = [
            {
                "type": "duplicate_billing_risk",
                "patient_id": str(r.patient_id),
                "claim_count": int(r.claim_count),
            }
            for r in rows
        ]
        return {"anomalies": anomalies, "total_anomalies": len(anomalies)}

    def get_duplicate_detection(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        claims = self.db.query(
            Claim.id,
            Claim.patient_id,
            Claim.incident_id,
        ).filter(Claim.tenant_id == tenant_id).all()

        seen: dict[str, list] = {}
        for c in claims:
            key = f"{c.patient_id}_{c.incident_id}"
            if key not in seen:
                seen[key] = []
            seen[key].append(str(c.id))

        duplicates = [
            {"key": k, "claim_ids": v, "count": len(v)}
            for k, v in seen.items()
            if len(v) > 1
        ]
        return {"duplicates": duplicates, "total_duplicate_groups": len(duplicates)}

    def get_stripe_reconciliation(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        plans = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.tenant_id == tenant_id
        ).all()
        active = [p for p in plans if p.status == "active"]
        past_due = [p for p in plans if p.status == "past_due"]

        # Compute MRR from subscription items joined with prices
        mrr_cents = 0
        if active:
            active_ids = [p.id for p in active]
            items = self.db.query(
                SubscriptionItem, Price
            ).join(Price, SubscriptionItem.price_id == Price.id).filter(
                SubscriptionItem.plan_id.in_(active_ids),
                Price.interval == "month",
            ).all()
            for item, price in items:
                mrr_cents += int(price.amount_cents or 0) * int(item.quantity or 1)

        return {
            "active_subscriptions": len(active),
            "past_due_subscriptions": len(past_due),
            "mrr_cents": mrr_cents,
            "as_of": datetime.now(UTC).isoformat(),
        }

    def get_churn_risk(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        at_risk_plans = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.tenant_id == tenant_id,
            SubscriptionPlan.status.in_(["past_due", "canceled", "paused"]),
        ).all()

        at_risk = []
        for plan in at_risk_plans:
            # Sum monthly amounts for each at-risk plan
            items = self.db.query(
                SubscriptionItem, Price
            ).join(Price, SubscriptionItem.price_id == Price.id).filter(
                SubscriptionItem.plan_id == plan.id,
                Price.interval == "month",
            ).all()
            monthly = sum(int(p.amount_cents or 0) * int(i.quantity or 1) for i, p in items)
            at_risk.append({
                "subscription_id": str(plan.id),
                "tenant_id": str(plan.tenant_id),
                "status": plan.status,
                "monthly_amount_cents": monthly,
            })
        return {"at_risk_subscriptions": at_risk, "count": len(at_risk)}

    def create_appeal_draft(
        self,
        tenant_id: uuid.UUID,
        claim_id: uuid.UUID,
        denial_reason: str,
        supporting_context: str = "",
    ) -> dict[str, Any] | None:
        claim = self.db.query(Claim).filter(
            Claim.tenant_id == tenant_id, Claim.id == claim_id
        ).first()
        if not claim:
            return None

        draft_text = (
            f"FORMAL APPEAL\n"
            f"Claim ID: {claim_id}\n"
            f"Payer: {claim.primary_payer_name or 'N/A'}\n\n"
            f"Denial Reason: {denial_reason}\n\n"
            f"We respectfully appeal this denial based on documented medical necessity and applicable coverage guidelines. "
            f"{supporting_context}\n\n"
            f"Supporting documentation is attached herewith.\n\nRespectfully,\nFusionEMS Billing Team\n"
        )
        review = AppealReview(
            claim_id=claim_id,
            denial_code=denial_reason[:32],
            draft_appeal_text=draft_text,
            status="PENDING",
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return {
            "id": str(review.id),
            "claim_id": str(review.claim_id),
            "denial_code": review.denial_code,
            "status": review.status,
            "letter": draft_text,
            "created_at": review.created_at.isoformat(),
        }

    def get_billing_alerts(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        alerts = []
        denied_count = self.db.query(func.count(Claim.id)).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.DENIED,
        ).scalar() or 0
        if denied_count > 50:
            alerts.append({"type": "high_denial_volume", "count": denied_count, "severity": "high"})

        overdue_count = self.db.query(func.count(PaymentLinkEvent.id)).join(
            Claim, PaymentLinkEvent.claim_id == Claim.id
        ).filter(
            Claim.tenant_id == tenant_id,
            PaymentLinkEvent.status == "EXPIRED",
        ).scalar() or 0
        if overdue_count > 0:
            alerts.append({"type": "overdue_payments", "count": overdue_count, "severity": "medium"})

        return {
            "alerts": alerts,
            "total": len(alerts),
            "as_of": datetime.now(UTC).isoformat(),
        }

    def get_payer_mix(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        rows = self.db.query(
            Claim.primary_payer_name,
            func.count(Claim.id).label("count"),
        ).filter(Claim.tenant_id == tenant_id).group_by(Claim.primary_payer_name).all()

        total = sum(int(r.count) for r in rows)
        payer_mix = [
            {
                "category": r.primary_payer_name or "UNKNOWN",
                "count": int(r.count),
                "pct": round(int(r.count) / total * 100, 2) if total else 0,
            }
            for r in rows
        ]
        return {"payer_mix": payer_mix, "total_claims": total}

    def get_tenant_billing_ranking(self) -> dict[str, Any]:
        rows = self.db.query(
            Tenant.id,
            Tenant.name,
            Tenant.billing_status,
            Tenant.billing_tier,
            func.count(Claim.id).label("claim_count"),
            func.sum(
                case((Claim.status == ClaimState.PAID, Claim.insurance_paid_cents), else_=0)
            ).label("revenue_cents"),
        ).outerjoin(Claim, Claim.tenant_id == Tenant.id).group_by(
            Tenant.id, Tenant.name, Tenant.billing_status, Tenant.billing_tier
        ).order_by(desc("revenue_cents")).limit(20).all()

        tenants = [
            {
                "tenant_id": str(r.id),
                "name": r.name,
                "billing_status": r.billing_status,
                "billing_tier": r.billing_tier,
                "claim_count": int(r.claim_count or 0),
                "revenue_cents": int(r.revenue_cents or 0),
            }
            for r in rows
        ]
        return {"tenants": tenants, "as_of": datetime.now(UTC).isoformat()}

    def batch_resubmit_claims(
        self,
        tenant_id: uuid.UUID,
        claim_ids: list[uuid.UUID],
        resubmit_reason: str,
        actor_user_id: uuid.UUID,
    ) -> dict[str, Any]:
        results = []
        for claim_id in claim_ids:
            claim = self.db.query(Claim).filter(
                Claim.tenant_id == tenant_id, Claim.id == claim_id
            ).first()
            if not claim:
                results.append({"claim_id": str(claim_id), "status": "not_found"})
                continue

            prev_status = str(claim.status)
            claim.status = ClaimState.READY_FOR_SUBMISSION
            audit = ClaimAuditEvent(
                claim_id=claim_id,
                user_id=actor_user_id,
                event_type="RESUBMIT",
                old_value=prev_status,
                new_value=str(ClaimState.READY_FOR_SUBMISSION),
                metadata_blob={"resubmit_reason": resubmit_reason},
            )
            self.db.add(audit)
            results.append({"claim_id": str(claim_id), "status": "resubmitted"})
        self.db.commit()
        return {"results": results, "total": len(results)}

    def predict_denial_risk(
        self,
        tenant_id: uuid.UUID,
        claim_id: uuid.UUID,
        payer_id: str,
        modifiers: list[str],
        actor_user_id: uuid.UUID,
    ) -> dict[str, Any]:
        payer_denied = self.db.query(func.count(Claim.id)).filter(
            Claim.tenant_id == tenant_id,
            Claim.primary_payer_id == payer_id,
            Claim.status == ClaimState.DENIED,
        ).scalar() or 0
        payer_total = self.db.query(func.count(Claim.id)).filter(
            Claim.tenant_id == tenant_id,
            Claim.primary_payer_id == payer_id,
        ).scalar() or 1

        risk_score = min(round(payer_denied / payer_total * 100, 2), 100)
        risk_flags = []
        if risk_score > 30:
            risk_flags.append("high_payer_denial_rate")
        if not modifiers:
            risk_flags.append("no_modifiers_attached")

        audit = ClaimAuditEvent(
            claim_id=claim_id,
            user_id=actor_user_id,
            event_type="DENIAL_RISK_SCORED",
            old_value=None,
            new_value=str(risk_score),
            metadata_blob={
                "payer_id": payer_id,
                "risk_score": risk_score,
                "risk_flags": risk_flags,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(audit)
        return {
            "claim_id": str(claim_id),
            "payer_id": payer_id,
            "risk_score": risk_score,
            "risk_flags": risk_flags,
            "audit_event_id": str(audit.id),
        }
