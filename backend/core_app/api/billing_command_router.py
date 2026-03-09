from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_role,
)
from core_app.billing.ar_aging import compute_revenue_forecast
from core_app.schemas.auth import CurrentUser
from core_app.services.billing_command_service import BillingCommandService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/billing-command", tags=["Billing Command"])


class DenialPredictionRequest(BaseModel):
    claim_id: uuid.UUID
    payer_id: str = ""
    procedure_codes: list[str] = Field(default_factory=list)
    diagnosis_codes: list[str] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)


class BatchResubmitRequest(BaseModel):
    claim_ids: list[uuid.UUID]
    resubmit_reason: str = "initial_denial"


class ContractSimRequest(BaseModel):
    payer_id: str
    proposed_rate_cents: int
    current_rate_cents: int
    annual_volume: int


class BillingAlertThresholdRequest(BaseModel):
    metric: str
    threshold_value: float
    alert_type: str = "email"
    recipients: list[str] = Field(default_factory=list)


class AppealDraftRequest(BaseModel):
    claim_id: uuid.UUID
    denial_reason: str
    supporting_context: str = ""


class PayerFollowUpRequest(BaseModel):
    payer_id: str
    claim_ids: list[uuid.UUID]
    follow_up_method: str = "phone"


@router.get("/dashboard")
async def revenue_dashboard(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_dashboard_metrics(current.tenant_id)


@router.get("/denial-heatmap")
async def denial_heatmap(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_denial_heatmap(current.tenant_id)


@router.get("/payer-performance")
async def payer_performance(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_payer_performance(current.tenant_id)


@router.get("/revenue-leakage")
async def revenue_leakage(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_revenue_leakage(current.tenant_id)


@router.get("/modifier-impact")
async def modifier_impact(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    try:
        rows = (
            db.execute(
                text(
                    "SELECT modifier, COUNT(*) as claim_count, SUM(total_billed_cents) as total_billed "
                    "FROM claims WHERE tenant_id = :tid AND modifier IS NOT NULL "
                    "GROUP BY modifier ORDER BY total_billed DESC LIMIT 20"
                ),
                {"tid": str(current.tenant_id)},
            )
            .mappings()
            .all()
        )
        return {"modifiers": [dict(r) for r in rows]}
    except Exception:
        logger.warning("modifier_impact query failed — modifier column may not exist yet", exc_info=True)
        return {"modifiers": []}


@router.get("/claim-lifecycle/{claim_id}")
async def claim_lifecycle(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    lifecycle = BillingCommandService(db).get_claim_lifecycle(current.tenant_id, claim_id)
    if not lifecycle:
        raise HTTPException(status_code=404, detail="claim_not_found")
    return lifecycle


@router.post("/denial-predictor")
async def predict_denial(
    body: DenialPredictionRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).predict_denial_risk(
        tenant_id=current.tenant_id,
        claim_id=body.claim_id,
        payer_id=body.payer_id,
        modifiers=body.modifiers,
        actor_user_id=current.user_id,
    )


@router.get("/appeal-success")
async def appeal_success_tracker(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_appeal_success(current.tenant_id)


@router.get("/billing-kpis")
async def billing_kpis(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_billing_kpis(current.tenant_id)


@router.post("/batch-resubmit")
async def batch_resubmit(
    body: BatchResubmitRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).batch_resubmit_claims(
        tenant_id=current.tenant_id,
        claim_ids=body.claim_ids,
        resubmit_reason=body.resubmit_reason,
        actor_user_id=current.user_id,
    )


@router.get("/fraud-anomaly")
async def fraud_anomaly(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_fraud_anomaly(current.tenant_id)


@router.get("/duplicate-detection")
async def duplicate_detection(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_duplicate_detection(current.tenant_id)


@router.post("/contract-simulation")
async def contract_simulation(
    body: ContractSimRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    current_annual = body.current_rate_cents * body.annual_volume
    proposed_annual = body.proposed_rate_cents * body.annual_volume
    delta = proposed_annual - current_annual
    return {
        "payer_id": body.payer_id,
        "current_annual_revenue_cents": current_annual,
        "proposed_annual_revenue_cents": proposed_annual,
        "delta_cents": delta,
        "delta_pct": round(delta / max(current_annual, 1) * 100, 2),
        "recommendation": "accept" if delta > 0 else "negotiate",
    }


@router.get("/stripe-reconciliation")
async def stripe_reconciliation(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_stripe_reconciliation(current.tenant_id)


@router.get("/churn-risk")
async def churn_risk(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_churn_risk(current.tenant_id)


@router.post("/appeal-draft")
async def ai_appeal_draft(
    body: AppealDraftRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    result = BillingCommandService(db).create_appeal_draft(
        tenant_id=current.tenant_id,
        claim_id=body.claim_id,
        denial_reason=body.denial_reason,
        supporting_context=body.supporting_context,
    )
    if not result:
        raise HTTPException(status_code=404, detail="claim_not_found")
    return {"draft": result, "letter": result["letter"]}


@router.get("/billing-alerts")
async def billing_alerts(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_billing_alerts(current.tenant_id)


@router.post("/alert-thresholds")
async def set_alert_threshold(
    body: BillingAlertThresholdRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    # TODO: Migrate when a typed BillingAlertThreshold model is added.
    require_role(current, ["founder", "admin"])
    return {
        "status": "accepted",
        "metric": body.metric,
        "threshold_value": body.threshold_value,
        "alert_type": body.alert_type,
        "recipients": body.recipients,
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.get("/revenue-by-service-level")
async def revenue_by_service_level(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    try:
        rows = (
            db.execute(
                text(
                    "SELECT service_level, COUNT(*) as claim_count, "
                    "SUM(total_billed_cents) as total_billed, SUM(insurance_paid_cents) as total_paid "
                    "FROM claims WHERE tenant_id = :tid AND service_level IS NOT NULL "
                    "GROUP BY service_level ORDER BY total_billed DESC"
                ),
                {"tid": str(current.tenant_id)},
            )
            .mappings()
            .all()
        )
        return {"service_levels": [dict(r) for r in rows]}
    except Exception:
        logger.warning("revenue_by_service_level query failed — service_level column may not exist yet", exc_info=True)
        return {"service_levels": []}


@router.get("/payer-mix")
async def payer_mix(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_payer_mix(current.tenant_id)


@router.get("/ar-concentration-risk")
async def ar_concentration_risk(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_ar_concentration_risk(current.tenant_id)


@router.get("/claim-throughput")
async def claim_throughput(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_claim_throughput(current.tenant_id)


@router.get("/revenue-trend")
async def revenue_trend(
    months: int = 6,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    forecast = compute_revenue_forecast(db, current.tenant_id, months=months)
    return forecast


@router.get("/billing-health")
async def billing_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin", "billing"])
    return BillingCommandService(db).get_billing_health(current.tenant_id)


@router.get("/tenant-billing-ranking")
async def tenant_billing_ranking(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    return BillingCommandService(db).get_tenant_billing_ranking()


@router.post("/payer-follow-up")
async def payer_follow_up(
    body: PayerFollowUpRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    # TODO: Migrate when a typed PayerFollowUp model is added.
    require_role(current, ["founder", "admin", "billing"])
    follow_ups = [
        {
            "claim_id": str(claim_id),
            "payer_id": body.payer_id,
            "method": body.follow_up_method,
            "status": "scheduled",
            "as_of": datetime.now(UTC).isoformat(),
        }
        for claim_id in body.claim_ids
    ]
    return {"follow_ups": follow_ups, "total": len(follow_ups)}


@router.get("/executive-summary")
async def executive_summary(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder", "admin"])
    summary = BillingCommandService(db).get_executive_summary(current.tenant_id)
    return {**summary, "as_of": datetime.now(UTC).isoformat()}


@router.get("/margin-risk")
async def margin_risk_by_tenant(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Per-tenant margin risk analysis — revenue vs cost exposure. Founder only."""
    require_role(current, ["founder"])
    return BillingCommandService(db).get_margin_risk_by_tenant()

