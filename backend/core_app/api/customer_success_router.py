"""
Customer Success API Router — Implementation Services, Support Operations,
Training & Enablement, Adoption & Health, Renewal & Expansion.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_role,
)
from core_app.schemas.auth import CurrentUser
from core_app.schemas.customer_success import (
    AccountHealthSnapshotResponse,
    AdoptionMetricResponse,
    ExpansionOpportunityCreate,
    ExpansionOpportunityResponse,
    ExpansionReadinessSignalResponse,
    GoLiveApprovalRequest,
    ImplementationProjectCreate,
    ImplementationProjectResponse,
    ImplementationProjectUpdate,
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    RenewalRiskSignalResponse,
    RiskFlagCreate,
    RiskFlagResponse,
    StabilizationCheckpointCreate,
    StabilizationCheckpointResponse,
    StakeholderEngagementNoteCreate,
    StakeholderEngagementNoteResponse,
    SupportEscalationCreate,
    SupportEscalationResponse,
    SupportNoteCreate,
    SupportNoteResponse,
    SupportResolutionRequest,
    SupportTicketCreate,
    SupportTicketResponse,
    SupportTransitionRequest,
    TrainingAssignmentCreate,
    TrainingAssignmentResponse,
    TrainingAssignmentUpdate,
    TrainingCompletionCreate,
    TrainingCompletionResponse,
    TrainingTrackCreate,
    TrainingTrackResponse,
    TrainingVerificationCreate,
    TrainingVerificationResponse,
    ValueMilestoneCreate,
    ValueMilestoneResponse,
    ValueMilestoneUpdate,
    WorkflowAdoptionMetricResponse,
)
from core_app.services.customer_success_service import CustomerSuccessService

router = APIRouter(prefix="/api/v1/customer-success", tags=["Customer Success"])


def _svc(db: Session) -> CustomerSuccessService:
    return CustomerSuccessService(db)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3: IMPLEMENTATION SERVICES
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/implementations", response_model=ImplementationProjectResponse)
def create_implementation(
    payload: ImplementationProjectCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ImplementationProjectResponse:
    svc = _svc(db)
    project = svc.create_implementation_project(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        name=payload.name,
        owner_user_id=payload.owner_user_id,
        target_go_live_date=payload.target_go_live_date,
        project_plan=payload.project_plan,
        go_live_criteria=payload.go_live_criteria,
        notes=payload.notes,
    )
    db.commit()
    return ImplementationProjectResponse.model_validate(project)


@router.get("/implementations", response_model=list[ImplementationProjectResponse])
def list_implementations(
    state: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[ImplementationProjectResponse]:
    svc = _svc(db)
    projects = svc.list_implementation_projects(current.tenant_id, state=state)
    return [ImplementationProjectResponse.model_validate(p) for p in projects]


@router.get("/implementations/{project_id}", response_model=ImplementationProjectResponse)
def get_implementation(
    project_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> ImplementationProjectResponse:
    svc = _svc(db)
    project = svc.get_implementation_project(current.tenant_id, project_id)
    return ImplementationProjectResponse.model_validate(project)


@router.patch("/implementations/{project_id}", response_model=ImplementationProjectResponse)
def update_implementation(
    project_id: UUID,
    payload: ImplementationProjectUpdate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ImplementationProjectResponse:
    svc = _svc(db)
    project = svc.update_implementation_project(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        project_id=project_id,
        **payload.model_dump(exclude_none=True),
    )
    db.commit()
    return ImplementationProjectResponse.model_validate(project)


@router.post(
    "/implementations/{project_id}/go-live",
    response_model=ImplementationProjectResponse,
)
def approve_go_live(
    project_id: UUID,
    payload: GoLiveApprovalRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ImplementationProjectResponse:
    svc = _svc(db)
    project = svc.approve_go_live(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        project_id=project_id,
        approved=payload.approved,
        reason=payload.reason,
    )
    db.commit()
    return ImplementationProjectResponse.model_validate(project)


# ── Milestones ────────────────────────────────────────────────────────────────


@router.post(
    "/implementations/{project_id}/milestones",
    response_model=MilestoneResponse,
)
def create_milestone(
    project_id: UUID,
    payload: MilestoneCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> MilestoneResponse:
    svc = _svc(db)
    ms = svc.create_milestone(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        owner_user_id=payload.owner_user_id,
        due_date=payload.due_date,
        sort_order=payload.sort_order,
        checklist_items=payload.checklist_items,
        dependencies=payload.dependencies,
    )
    db.commit()
    return MilestoneResponse.model_validate(ms)


@router.get(
    "/implementations/{project_id}/milestones",
    response_model=list[MilestoneResponse],
)
def list_milestones(
    project_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[MilestoneResponse]:
    svc = _svc(db)
    milestones = svc.list_milestones(current.tenant_id, project_id)
    return [MilestoneResponse.model_validate(m) for m in milestones]


@router.patch("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update_milestone(
    milestone_id: UUID,
    payload: MilestoneUpdate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> MilestoneResponse:
    svc = _svc(db)
    ms = svc.update_milestone_status(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        milestone_id=milestone_id,
        new_status=payload.status or "",
        reason=payload.reason,
    )
    db.commit()
    return MilestoneResponse.model_validate(ms)


# ── Risk Flags ────────────────────────────────────────────────────────────────


@router.post(
    "/implementations/{project_id}/risk-flags",
    response_model=RiskFlagResponse,
)
def add_risk_flag(
    project_id: UUID,
    payload: RiskFlagCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> RiskFlagResponse:
    svc = _svc(db)
    flag = svc.add_risk_flag(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        source=payload.source,
    )
    db.commit()
    return RiskFlagResponse.model_validate(flag)


@router.post("/risk-flags/{flag_id}/resolve", response_model=RiskFlagResponse)
def resolve_risk_flag(
    flag_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> RiskFlagResponse:
    svc = _svc(db)
    flag = svc.resolve_risk_flag(current.tenant_id, current.user_id, flag_id)
    db.commit()
    return RiskFlagResponse.model_validate(flag)


# ── Stabilization Checkpoints ─────────────────────────────────────────────────


@router.post(
    "/implementations/{project_id}/stabilization",
    response_model=StabilizationCheckpointResponse,
)
def add_stabilization_checkpoint(
    project_id: UUID,
    payload: StabilizationCheckpointCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> StabilizationCheckpointResponse:
    svc = _svc(db)
    cp = svc.add_stabilization_checkpoint(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        project_id=project_id,
        checkpoint_name=payload.checkpoint_name,
        is_passed=False,
        findings=payload.findings,
    )
    db.commit()
    return StabilizationCheckpointResponse.model_validate(cp)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: SUPPORT OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/support/tickets", response_model=SupportTicketResponse)
def create_ticket(
    payload: SupportTicketCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> SupportTicketResponse:
    svc = _svc(db)
    ticket = svc.create_support_ticket(
        tenant_id=current.tenant_id,
        reporter_user_id=current.user_id,
        subject=payload.subject,
        description=payload.description,
        severity=payload.severity,
        category=payload.category,
        linked_workflow_id=payload.linked_workflow_id,
        linked_incident_id=payload.linked_incident_id,
        linked_claim_id=payload.linked_claim_id,
        context_metadata=payload.context_metadata,
    )
    db.commit()
    return SupportTicketResponse.model_validate(ticket)


@router.get("/support/tickets", response_model=list[SupportTicketResponse])
def list_tickets(
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[SupportTicketResponse]:
    svc = _svc(db)
    tickets = svc.list_support_tickets(
        current.tenant_id, status=status, severity=severity,
    )
    return [SupportTicketResponse.model_validate(t) for t in tickets]


@router.get("/support/tickets/{ticket_id}", response_model=SupportTicketResponse)
def get_ticket(
    ticket_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> SupportTicketResponse:
    svc = _svc(db)
    ticket = svc.get_support_ticket(current.tenant_id, ticket_id)
    return SupportTicketResponse.model_validate(ticket)


@router.post(
    "/support/tickets/{ticket_id}/transition",
    response_model=SupportTicketResponse,
)
def transition_ticket(
    ticket_id: UUID,
    payload: SupportTransitionRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> SupportTicketResponse:
    svc = _svc(db)
    ticket = svc.transition_support_ticket(
        current.tenant_id, current.user_id, ticket_id,
        payload.new_state, payload.reason,
    )
    db.commit()
    return SupportTicketResponse.model_validate(ticket)


@router.post(
    "/support/tickets/{ticket_id}/notes",
    response_model=SupportNoteResponse,
)
def add_note(
    ticket_id: UUID,
    payload: SupportNoteCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> SupportNoteResponse:
    svc = _svc(db)
    note = svc.add_support_note(
        current.tenant_id, current.user_id, ticket_id,
        payload.content, payload.visibility,
    )
    db.commit()
    return SupportNoteResponse.model_validate(note)


@router.post(
    "/support/tickets/{ticket_id}/escalate",
    response_model=SupportEscalationResponse,
)
def escalate_ticket(
    ticket_id: UUID,
    payload: SupportEscalationCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> SupportEscalationResponse:
    svc = _svc(db)
    esc = svc.escalate_ticket(
        current.tenant_id, current.user_id, ticket_id,
        payload.reason, payload.new_severity, payload.escalated_to_user_id,
    )
    db.commit()
    return SupportEscalationResponse.model_validate(esc)


@router.post(
    "/support/tickets/{ticket_id}/resolve",
    response_model=SupportTicketResponse,
)
def resolve_ticket(
    ticket_id: UUID,
    payload: SupportResolutionRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> SupportTicketResponse:
    svc = _svc(db)
    ticket = svc.resolve_ticket(
        current.tenant_id, current.user_id, ticket_id,
        payload.resolution_code, payload.summary,
    )
    db.commit()
    return SupportTicketResponse.model_validate(ticket)


@router.post(
    "/support/tickets/{ticket_id}/reopen",
    response_model=SupportTicketResponse,
)
def reopen_ticket(
    ticket_id: UUID,
    payload: SupportTransitionRequest,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> SupportTicketResponse:
    svc = _svc(db)
    ticket = svc.reopen_ticket(
        current.tenant_id, current.user_id, ticket_id,
        payload.reason or "Reopened by user",
    )
    db.commit()
    return SupportTicketResponse.model_validate(ticket)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5: TRAINING & ENABLEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/training/tracks", response_model=TrainingTrackResponse)
def create_training_track(
    payload: TrainingTrackCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> TrainingTrackResponse:
    svc = _svc(db)
    track = svc.create_training_track(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        name=payload.name,
        description=payload.description,
        target_role=payload.target_role,
        module_type=payload.module_type,
        sort_order=payload.sort_order,
        curriculum=payload.curriculum,
        estimated_duration_minutes=payload.estimated_duration_minutes,
    )
    db.commit()
    return TrainingTrackResponse.model_validate(track)


@router.get("/training/tracks", response_model=list[TrainingTrackResponse])
def list_training_tracks(
    role: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[TrainingTrackResponse]:
    svc = _svc(db)
    tracks = svc.list_training_tracks(current.tenant_id, role=role)
    return [TrainingTrackResponse.model_validate(t) for t in tracks]


@router.post("/training/assignments", response_model=TrainingAssignmentResponse)
def assign_training(
    payload: TrainingAssignmentCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> TrainingAssignmentResponse:
    svc = _svc(db)
    assignment = svc.assign_training(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        track_id=payload.track_id,
        user_id=payload.user_id,
        due_date=payload.due_date,
    )
    db.commit()
    return TrainingAssignmentResponse.model_validate(assignment)


@router.get("/training/assignments", response_model=list[TrainingAssignmentResponse])
def list_training_assignments(
    user_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[TrainingAssignmentResponse]:
    svc = _svc(db)
    assignments = svc.list_training_assignments(
        current.tenant_id, user_id=user_id, status=status,
    )
    return [TrainingAssignmentResponse.model_validate(a) for a in assignments]


@router.patch(
    "/training/assignments/{assignment_id}",
    response_model=TrainingAssignmentResponse,
)
def update_training_assignment(
    assignment_id: UUID,
    payload: TrainingAssignmentUpdate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> TrainingAssignmentResponse:
    svc = _svc(db)
    assignment = svc.update_training_assignment(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        assignment_id=assignment_id,
        status=payload.status,
        progress_pct=payload.progress_pct,
        due_date=payload.due_date,
    )
    db.commit()
    return TrainingAssignmentResponse.model_validate(assignment)


@router.post(
    "/training/assignments/{assignment_id}/completions",
    response_model=TrainingCompletionResponse,
)
def record_completion(
    assignment_id: UUID,
    payload: TrainingCompletionCreate,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> TrainingCompletionResponse:
    svc = _svc(db)
    completion = svc.record_training_completion(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        assignment_id=assignment_id,
        module_key=payload.module_key,
        score=payload.score,
        evidence=payload.evidence,
    )
    db.commit()
    return TrainingCompletionResponse.model_validate(completion)


@router.post(
    "/training/assignments/{assignment_id}/verify",
    response_model=TrainingVerificationResponse,
)
def verify_training(
    assignment_id: UUID,
    payload: TrainingVerificationCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> TrainingVerificationResponse:
    svc = _svc(db)
    verification = svc.verify_training(
        tenant_id=current.tenant_id,
        verifier_user_id=current.user_id,
        assignment_id=assignment_id,
        is_verified=payload.is_verified,
        notes=payload.notes,
    )
    db.commit()
    return TrainingVerificationResponse.model_validate(verification)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6: ADOPTION & HEALTH
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/health/compute", response_model=AccountHealthSnapshotResponse)
def compute_health(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> AccountHealthSnapshotResponse:
    svc = _svc(db)
    snapshot = svc.compute_account_health(current.tenant_id, trigger="MANUAL")
    db.commit()
    return AccountHealthSnapshotResponse.model_validate(snapshot)


@router.get("/health/latest", response_model=AccountHealthSnapshotResponse | None)
def get_latest_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> AccountHealthSnapshotResponse | None:
    svc = _svc(db)
    snapshot = svc.get_latest_health_snapshot(current.tenant_id)
    if snapshot is None:
        return None
    return AccountHealthSnapshotResponse.model_validate(snapshot)


@router.get("/adoption/metrics", response_model=list[AdoptionMetricResponse])
def list_adoption_metrics(
    module_name: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[AdoptionMetricResponse]:
    svc = _svc(db)
    metrics = svc.list_adoption_metrics(current.tenant_id, module_name=module_name)
    return [AdoptionMetricResponse.model_validate(m) for m in metrics]


@router.get(
    "/adoption/workflows",
    response_model=list[WorkflowAdoptionMetricResponse],
)
def list_workflow_adoption(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[WorkflowAdoptionMetricResponse]:
    svc = _svc(db)
    metrics = svc.list_workflow_adoption_metrics(current.tenant_id)
    return [WorkflowAdoptionMetricResponse.model_validate(m) for m in metrics]


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7: RENEWAL & EXPANSION
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/renewal/risks", response_model=list[RenewalRiskSignalResponse])
def list_renewal_risks(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[RenewalRiskSignalResponse]:
    svc = _svc(db)
    signals = svc.list_renewal_risk_signals(current.tenant_id)
    return [RenewalRiskSignalResponse.model_validate(s) for s in signals]


@router.post("/expansion/opportunities", response_model=ExpansionOpportunityResponse)
def create_expansion_opportunity(
    payload: ExpansionOpportunityCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ExpansionOpportunityResponse:
    svc = _svc(db)
    opp = svc.create_expansion_opportunity(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        module_name=payload.module_name,
        opportunity_type=payload.opportunity_type,
        recommended_action=payload.recommended_action,
        evidence=payload.evidence,
        estimated_value_cents=payload.estimated_value_cents,
    )
    db.commit()
    return ExpansionOpportunityResponse.model_validate(opp)


@router.get(
    "/expansion/opportunities",
    response_model=list[ExpansionOpportunityResponse],
)
def list_expansion_opportunities(
    state: str | None = Query(default=None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[ExpansionOpportunityResponse]:
    svc = _svc(db)
    opps = svc.list_expansion_opportunities(current.tenant_id, state=state)
    return [ExpansionOpportunityResponse.model_validate(o) for o in opps]


@router.get(
    "/expansion/readiness",
    response_model=list[ExpansionReadinessSignalResponse],
)
def list_expansion_readiness(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[ExpansionReadinessSignalResponse]:
    svc = _svc(db)
    signals = svc.get_expansion_ready_signals()
    return [ExpansionReadinessSignalResponse.model_validate(s) for s in signals]


@router.post("/stakeholder-notes", response_model=StakeholderEngagementNoteResponse)
def add_stakeholder_note(
    payload: StakeholderEngagementNoteCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> StakeholderEngagementNoteResponse:
    svc = _svc(db)
    note = svc.add_stakeholder_note(
        tenant_id=current.tenant_id,
        author_user_id=current.user_id,
        stakeholder_name=payload.stakeholder_name,
        stakeholder_role=payload.stakeholder_role,
        engagement_type=payload.engagement_type,
        content=payload.content,
        sentiment=payload.sentiment,
    )
    db.commit()
    return StakeholderEngagementNoteResponse.model_validate(note)


@router.get(
    "/stakeholder-notes",
    response_model=list[StakeholderEngagementNoteResponse],
)
def list_stakeholder_notes(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[StakeholderEngagementNoteResponse]:
    svc = _svc(db)
    notes = svc.list_stakeholder_notes(current.tenant_id)
    return [StakeholderEngagementNoteResponse.model_validate(n) for n in notes]


@router.post("/value-milestones", response_model=ValueMilestoneResponse)
def create_value_milestone(
    payload: ValueMilestoneCreate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ValueMilestoneResponse:
    svc = _svc(db)
    vm = svc.create_value_milestone(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        milestone_name=payload.milestone_name,
        category=payload.category,
        description=payload.description,
        evidence=payload.evidence,
        impact_summary=payload.impact_summary,
    )
    db.commit()
    return ValueMilestoneResponse.model_validate(vm)


@router.post(
    "/value-milestones/{milestone_id}/achieve",
    response_model=ValueMilestoneResponse,
)
def achieve_value_milestone(
    milestone_id: UUID,
    payload: ValueMilestoneUpdate,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ValueMilestoneResponse:
    svc = _svc(db)
    vm = svc.achieve_value_milestone(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        milestone_id=milestone_id,
        evidence=payload.evidence,
        impact_summary=payload.impact_summary,
    )
    db.commit()
    return ValueMilestoneResponse.model_validate(vm)


@router.get("/value-milestones", response_model=list[ValueMilestoneResponse])
def list_value_milestones(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> list[ValueMilestoneResponse]:
    svc = _svc(db)
    vms = svc.list_value_milestones(current.tenant_id)
    return [ValueMilestoneResponse.model_validate(v) for v in vms]
