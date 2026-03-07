from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from core_app.models.billing import Claim, ClaimState, ClaimIssue, PatientBalanceState
from core_app.models.pricing import Price, SubscriptionPlan, Product
from core_app.models.agency import AgencyBillingPolicy

class BillingCommandService:
    """
    Production service for the Founder Billing Command Center.
    Replaces schemaless mock repos with fully-typed SQLAlchemy access.
    """
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_metrics(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
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

    def get_denial_heatmap(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        issues = self.db.query(
            ClaimIssue.what_is_wrong,
            func.count(ClaimIssue.id).label("count")
        ).join(Claim, ClaimIssue.claim_id == Claim.id).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.DENIED,
            ClaimIssue.resolved == False
        ).group_by(ClaimIssue.what_is_wrong).order_by(func.count(ClaimIssue.id).desc()).all()

        total_denials = sum(iss.count for iss in issues) if issues else 0
        heatmap = [{"reason_code": iss.what_is_wrong, "count": iss.count} for iss in issues]

        return {
            "heatmap": heatmap,
            "total_denials": total_denials,
            "top_reason": heatmap[0]["reason_code"] if heatmap else None
        }

    def get_payer_performance(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
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
                "avg_days_to_payment": 14 # Static until lifecycle events are modeled with hard days
            })

        return {"payers": payers}

    def get_executive_summary(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        # Include MRR and total revenue
        # Here we connect SaaS and Claims
        claim_rev = self.db.query(func.sum(Claim.insurance_paid_cents)).filter(
            Claim.tenant_id == tenant_id, 
            Claim.status == ClaimState.PAID
        ).scalar() or 0

        # Current subscription sum - assuming it's monthly
        # Mocking MRR from SubscriptionPlan / Price logic for now since exact items query needs joins
        mrr_cents = 0 # Future: actual sum across SubscriptionItems
        
        return {
            "total_revenue_cents": claim_rev,
            "mrr_cents": mrr_cents,
            "arr_cents": mrr_cents * 12
        }

    def get_revenue_leakage(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        # Revenue leakage = unresolved denials, missing secondary, open patient balances that are aging
        leakage_items = []
        # Find unappealed denials
        unappealed = self.db.query(Claim).filter(
            Claim.tenant_id == tenant_id,
            Claim.status == ClaimState.DENIED,
            Claim.appeal_status == None
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
