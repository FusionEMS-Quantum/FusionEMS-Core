"""
Founder Operations Command Router — Module 6 of FINAL_BUILD_STATEMENT.

Exposes aggregated operational intelligence across all domains:
- Deployment issues
- Payment failures
- Claims pipeline (ready, blocked, denied, appeals)
- High-risk denials
- Patient balance review
- Collections review
- Debt-setoff review
- Tax/agency profile gaps
- Billing communications health
- CrewLink paging health
- Top 3 actionable items
- Full ops summary
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_founder_only_audited,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.founder_ops_service import FounderOpsService

router = APIRouter(
    prefix="/api/v1/founder/ops",
    tags=["Founder Operations"],
    dependencies=[Depends(require_founder_only_audited())],
)


def _svc(db: Session) -> FounderOpsService:
    return FounderOpsService(db)


@router.get("/summary")
async def ops_summary(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Complete founder ops summary — answers all Module 6 questions."""
    return _svc(db).get_ops_summary()


@router.get("/deployment-issues")
async def deployment_issues(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Active deployment failures, retries, and blocked runs."""
    return _svc(db).get_deployment_issues()


@router.get("/payment-failures")
async def payment_failures(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Stripe payment failures, expired methods, past-due invoices."""
    return _svc(db).get_payment_failures()


@router.get("/claims-pipeline")
async def claims_pipeline(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Ready-to-submit, blocked, denied, and appeal claims overview."""
    return _svc(db).get_claims_pipeline()


@router.get("/high-risk-denials")
async def high_risk_denials(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Denied claims with high financial impact and no appeal started."""
    return _svc(db).get_high_risk_denials()


@router.get("/patient-balances")
async def patient_balances(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Patient balance summary by state across all claims."""
    return _svc(db).get_patient_balance_review()


@router.get("/collections-review")
async def collections_review(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Pending collections reviews and escalation status."""
    return _svc(db).get_collections_review()


@router.get("/debt-setoff")
async def debt_setoff(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Debt-setoff enrollment and batch status overview."""
    return _svc(db).get_debt_setoff_review()


@router.get("/profile-gaps")
async def profile_gaps(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Agencies missing tax, public-sector, or billing profiles."""
    return _svc(db).get_profile_gaps()


@router.get("/comms-health")
async def comms_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Billing communications health across SMS/email/voice channels."""
    return _svc(db).get_comms_health()


@router.get("/crewlink-health")
async def crewlink_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """CrewLink paging health — active alerts, response times, escalations."""
    return _svc(db).get_crewlink_health()


@router.get("/top-actions")
async def top_actions(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Top 3 most urgent actions across all domains."""
    return _svc(db).get_top_actions()
