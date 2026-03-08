"""Third-party billing portal API — scoped to agency billing workflows.

Provides dashboard, claims workspace, AR, denials, payments, documents,
communications, and compliance endpoints for authorized third-party billers.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.services.billing_command_service import BillingCommandService
from core_app.services.export_offboarding_service import ExportOffboardingService

router = APIRouter(
    prefix="/api/v1/portal/billing",
    tags=["Third-Party Billing Portal"],
)

PORTAL_ROLES = ("founder", "admin", "agency_admin", "billing")


# ── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def portal_dashboard(
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Realtime billing dashboard for third-party billing portal."""
    svc = ExportOffboardingService(db)
    dashboard = svc.get_portal_dashboard(current.tenant_id)

    # Enrich with billing command KPIs
    billing_svc = BillingCommandService(db)
    kpis = billing_svc.get_billing_kpis(current.tenant_id)
    dashboard["billing_kpis"] = kpis

    denial_heatmap = billing_svc.get_denial_heatmap(current.tenant_id)
    dashboard["denial_heatmap"] = denial_heatmap

    payer_perf = billing_svc.get_payer_performance(current.tenant_id)
    dashboard["payer_performance"] = payer_perf

    return dashboard


# ── Claims Workspace ─────────────────────────────────────────────────────────

@router.get("/claims")
async def list_claims(
    status_filter: str | None = Query(default=None, alias="status"),
    payer: str | None = Query(default=None),
    aging_min: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """List claims with filters for the billing workspace."""
    svc = ExportOffboardingService(db)
    claims = svc.list_claims(
        tenant_id=current.tenant_id,
        status_filter=status_filter,
        payer_filter=payer,
        aging_min=aging_min,
        limit=limit,
        offset=offset,
    )
    return {"claims": claims, "count": len(claims)}


@router.get("/claims/{claim_id}")
async def get_claim_detail(
    claim_id: uuid.UUID,
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Full claim detail with audit trail, issues, appeals, and communications."""
    svc = ExportOffboardingService(db)
    detail = svc.get_claim_detail(current.tenant_id, claim_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return detail


# ── Denials ──────────────────────────────────────────────────────────────────

@router.get("/denials")
async def list_denials(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """List denied claims for the denial work queue."""
    svc = ExportOffboardingService(db)
    claims = svc.list_claims(
        tenant_id=current.tenant_id,
        status_filter="DENIED",
        limit=limit,
        offset=offset,
    )
    billing_svc = BillingCommandService(db)
    heatmap = billing_svc.get_denial_heatmap(current.tenant_id)
    return {"denied_claims": claims, "count": len(claims), "heatmap": heatmap}


# ── AR / Payments ────────────────────────────────────────────────────────────

@router.get("/ar")
async def ar_overview(
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """AR aging overview for the portal."""
    billing_svc = BillingCommandService(db)
    concentration = billing_svc.get_ar_concentration_risk(current.tenant_id)
    leakage = billing_svc.get_revenue_leakage(current.tenant_id)
    return {"ar_concentration": concentration, "revenue_leakage": leakage}


@router.get("/payments")
async def payment_overview(
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Payment posting summary for the portal."""
    billing_svc = BillingCommandService(db)
    exec_summary = billing_svc.get_executive_summary(current.tenant_id)
    return {"payment_summary": exec_summary}


# ── Documents ────────────────────────────────────────────────────────────────

@router.get("/documents")
async def list_documents(
    doc_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """List documents available for the tenant (PCRs, facesheets, statements, etc.)."""
    # Documents are stored via DominationService generic records
    from core_app.services.domination_service import DominationService
    from core_app.services.event_publisher import get_event_publisher

    svc = DominationService(db, get_event_publisher())
    filters: dict[str, Any] = {}
    if doc_type:
        filters["doc_type"] = doc_type
    docs = svc.repo("documents").list(tenant_id=current.tenant_id, filters=filters, limit=limit)
    return {"documents": docs, "count": len(docs)}


# ── Communications ───────────────────────────────────────────────────────────

@router.get("/communications")
async def list_communications(
    limit: int = Query(default=100, ge=1, le=500),
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Billing communications history (SMS, calls, escalations)."""
    from core_app.services.domination_service import DominationService
    from core_app.services.event_publisher import get_event_publisher

    svc = DominationService(db, get_event_publisher())
    threads = svc.repo("billing_sms_threads").list(tenant_id=current.tenant_id, limit=limit)
    messages = svc.repo("billing_sms_messages").list(tenant_id=current.tenant_id, limit=limit)
    return {"threads": threads, "messages": messages}


# ── Compliance ───────────────────────────────────────────────────────────────

@router.get("/compliance")
async def compliance_overview(
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Compliance posture for billing operations."""
    billing_svc = BillingCommandService(db)
    health = billing_svc.get_billing_health(current.tenant_id)
    kpis = billing_svc.get_billing_kpis(current.tenant_id)
    return {
        "billing_health": health,
        "kpis": kpis,
        "audit_trail_available": True,
        "export_available": True,
    }


# ── Analytics ────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def billing_analytics(
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Premium billing analytics for the portal."""
    billing_svc = BillingCommandService(db)
    return {
        "dashboard": billing_svc.get_dashboard_metrics(current.tenant_id),
        "denial_heatmap": billing_svc.get_denial_heatmap(current.tenant_id),
        "payer_performance": billing_svc.get_payer_performance(current.tenant_id),
        "ar_concentration": billing_svc.get_ar_concentration_risk(current.tenant_id),
        "revenue_leakage": billing_svc.get_revenue_leakage(current.tenant_id),
        "executive_summary": billing_svc.get_executive_summary(current.tenant_id),
    }


# ── Field Crosswalk ──────────────────────────────────────────────────────────

@router.get("/field-crosswalk")
async def field_crosswalk(
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Get the field crosswalk mapping for data exports."""
    svc = ExportOffboardingService(db)
    return {"crosswalk": svc.get_field_crosswalk()}
