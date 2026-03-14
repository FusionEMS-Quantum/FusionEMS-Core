"""
Founder Success Command Center Router — Part 8 of the directive.

Aggregated views for the founder across implementation, support,
training, adoption, and expansion domains.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    require_founder_only_audited,
)
from core_app.schemas.auth import CurrentUser
from core_app.schemas.customer_success import (
    AccountHealthSnapshotResponse,
    AdoptionMetricResponse,
    ExpansionReadinessSignalResponse,
    FounderSuccessSummary,
    ImplementationHealthScore,
    ImplementationProjectResponse,
    SuccessAction,
    SupportQueueHealth,
    SupportTicketResponse,
    TrainingAssignmentResponse,
    TrainingCompletionSummary,
)
from core_app.services.customer_success_service import CustomerSuccessService

router = APIRouter(
    prefix="/api/v1/founder/success-command",
    tags=["Founder Success Command Center"],
)

_FOUNDER = Depends(require_founder_only_audited())


def _svc(db: Session) -> CustomerSuccessService:
    return CustomerSuccessService(db)


@router.get("/summary", response_model=FounderSuccessSummary)
def founder_success_summary(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> FounderSuccessSummary:
    """Full aggregated success summary for the founder dashboard."""
    svc = _svc(db)

    stalled = svc.get_stalled_implementations()
    high_sev = svc.get_high_severity_tickets()
    at_risk = svc.get_at_risk_accounts()
    training_gap_items = svc.get_training_gaps()
    low_adoption = svc.get_low_adoption_modules()
    expansion_ready = svc.get_expansion_ready_signals()

    actions: list[SuccessAction] = []

    for proj in stalled:
        actions.append(SuccessAction(
            domain="implementation",
            severity="high",
            summary=f"Stalled implementation: {proj.name} (state: {proj.state})",
            recommended_action="Escalate to project owner and review blockers",
            entity_id=proj.id,
        ))

    for ticket in high_sev:
        actions.append(SuccessAction(
            domain="support",
            severity="critical" if ticket.severity == "CRITICAL" else "high",
            summary=f"High-severity ticket: {ticket.subject} ({ticket.severity})",
            recommended_action="Assign senior support and escalate if SLA at risk",
            entity_id=ticket.id,
        ))

    for snap in at_risk:
        actions.append(SuccessAction(
            domain="health",
            severity="high",
            summary=f"At-risk account: tenant {snap.tenant_id} (score: {snap.overall_score})",
            recommended_action="Schedule executive review and remediation plan",
            entity_id=snap.id,
        ))

    for gap in training_gap_items:
        actions.append(SuccessAction(
            domain="training",
            severity="medium",
            summary=f"Training overdue: assignment {gap.id} (status: {gap.status})",
            recommended_action="Contact user and extend deadline or reassign",
            entity_id=gap.id,
        ))

    for metric in low_adoption:
        actions.append(SuccessAction(
            domain="adoption",
            severity="medium",
            summary=f"Low adoption: {metric.module_name} ({metric.metric_value}%)",
            recommended_action="Schedule enablement session for the module",
            entity_id=metric.id,
        ))

    actions.sort(key=lambda a: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(a.severity, 3))
    top_actions = actions[:3]

    return FounderSuccessSummary(
        stalled_implementations=len(stalled),
        high_severity_tickets=len(high_sev),
        at_risk_accounts=len(at_risk),
        training_gaps=len(training_gap_items),
        low_adoption_modules=len(low_adoption),
        expansion_ready_signals=len(expansion_ready),
        top_actions=top_actions,
    )


@router.get(
    "/stalled-implementations",
    response_model=list[ImplementationProjectResponse],
)
def stalled_implementations(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> list[ImplementationProjectResponse]:
    svc = _svc(db)
    projects = svc.get_stalled_implementations()
    return [ImplementationProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/high-severity-tickets",
    response_model=list[SupportTicketResponse],
)
def high_severity_tickets(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> list[SupportTicketResponse]:
    svc = _svc(db)
    tickets = svc.get_high_severity_tickets()
    return [SupportTicketResponse.model_validate(t) for t in tickets]


@router.get(
    "/at-risk-accounts",
    response_model=list[AccountHealthSnapshotResponse],
)
def at_risk_accounts(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> list[AccountHealthSnapshotResponse]:
    svc = _svc(db)
    snapshots = svc.get_at_risk_accounts()
    return [AccountHealthSnapshotResponse.model_validate(s) for s in snapshots]


@router.get(
    "/training-gaps",
    response_model=list[TrainingAssignmentResponse],
)
def training_gaps(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> list[TrainingAssignmentResponse]:
    svc = _svc(db)
    gaps = svc.get_training_gaps()
    return [TrainingAssignmentResponse.model_validate(g) for g in gaps]


@router.get(
    "/low-adoption-modules",
    response_model=list[AdoptionMetricResponse],
)
def low_adoption_modules(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> list[AdoptionMetricResponse]:
    svc = _svc(db)
    metrics = svc.get_low_adoption_modules()
    return [AdoptionMetricResponse.model_validate(m) for m in metrics]


@router.get(
    "/expansion-readiness",
    response_model=list[ExpansionReadinessSignalResponse],
)
def expansion_readiness(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> list[ExpansionReadinessSignalResponse]:
    svc = _svc(db)
    signals = svc.get_expansion_ready_signals()
    return [ExpansionReadinessSignalResponse.model_validate(s) for s in signals]


@router.get("/implementation-health", response_model=ImplementationHealthScore)
def implementation_health(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> ImplementationHealthScore:
    svc = _svc(db)
    score_data = svc.get_implementation_health_score()
    return ImplementationHealthScore(**score_data)


@router.get("/support-queue-health", response_model=SupportQueueHealth)
def support_queue_health(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> SupportQueueHealth:
    svc = _svc(db)
    health_data = svc.get_support_queue_health()
    return SupportQueueHealth(**health_data)


@router.get("/training-completion", response_model=TrainingCompletionSummary)
def training_completion(
    current: CurrentUser = _FOUNDER,
    db: Session = Depends(db_session_dependency),
) -> TrainingCompletionSummary:
    svc = _svc(db)
    summary_data = svc.get_training_completion_summary()
    return TrainingCompletionSummary(**summary_data)
