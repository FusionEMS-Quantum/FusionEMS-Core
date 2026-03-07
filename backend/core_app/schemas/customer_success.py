"""Pydantic schemas for the Customer Success platform."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ═══════════════════════════════════════════════════════════════════════════════
# PART 3: IMPLEMENTATION SERVICES
# ═══════════════════════════════════════════════════════════════════════════════


class ImplementationProjectCreate(BaseModel):
    name: str
    owner_user_id: UUID
    target_go_live_date: datetime | None = None
    project_plan: dict = Field(default_factory=dict)
    go_live_criteria: dict = Field(default_factory=dict)
    notes: str | None = None


class ImplementationProjectUpdate(BaseModel):
    name: str | None = None
    state: str | None = None
    target_go_live_date: datetime | None = None
    actual_go_live_date: datetime | None = None
    stabilization_end_date: datetime | None = None
    project_plan: dict | None = None
    go_live_criteria: dict | None = None
    notes: str | None = None


class ImplementationProjectResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    state: str
    owner_user_id: UUID
    target_go_live_date: datetime | None
    actual_go_live_date: datetime | None
    stabilization_end_date: datetime | None
    handoff_completed_at: datetime | None
    project_plan: dict
    go_live_criteria: dict
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MilestoneCreate(BaseModel):
    name: str
    description: str
    owner_user_id: UUID
    due_date: datetime
    sort_order: int = 0
    checklist_items: list = Field(default_factory=list)
    dependencies: list = Field(default_factory=list)


class MilestoneUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    owner_user_id: UUID | None = None
    due_date: datetime | None = None
    reason: str | None = None


class MilestoneResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    name: str
    description: str
    status: str
    owner_user_id: UUID
    due_date: datetime
    completed_at: datetime | None
    sort_order: int
    checklist_items: dict
    dependencies: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskFlagCreate(BaseModel):
    title: str
    description: str
    severity: str
    source: str = "MANUAL"


class RiskFlagResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    severity: str
    title: str
    description: str
    source: str
    is_resolved: bool
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StabilizationCheckpointCreate(BaseModel):
    checkpoint_name: str
    findings: dict = Field(default_factory=dict)


class StabilizationCheckpointResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID
    checkpoint_name: str
    checked_by_user_id: UUID
    is_passed: bool
    findings: dict
    checked_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingLinkCreate(BaseModel):
    training_assignment_id: UUID
    is_blocking: bool = True


class TrainingLinkResponse(BaseModel):
    id: UUID
    milestone_id: UUID
    training_assignment_id: UUID
    is_blocking: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoLiveApprovalRequest(BaseModel):
    approved: bool
    reason: str


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: SUPPORT OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════


class SupportTicketCreate(BaseModel):
    subject: str
    description: str
    severity: str = "MEDIUM"
    category: str | None = None
    linked_workflow_id: UUID | None = None
    linked_incident_id: UUID | None = None
    linked_claim_id: UUID | None = None
    context_metadata: dict = Field(default_factory=dict)


class SupportTicketUpdate(BaseModel):
    subject: str | None = None
    severity: str | None = None
    assigned_to_user_id: UUID | None = None
    category: str | None = None


class SupportTicketResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    subject: str
    description: str
    status: str
    severity: str
    reporter_user_id: UUID
    assigned_to_user_id: UUID | None
    category: str | None
    linked_workflow_id: UUID | None
    linked_incident_id: UUID | None
    linked_claim_id: UUID | None
    context_metadata: dict
    resolution_code: str | None
    resolution_summary: str | None
    resolved_at: datetime | None
    closed_at: datetime | None
    reopened_at: datetime | None
    sla_response_due_at: datetime | None
    sla_resolution_due_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportNoteCreate(BaseModel):
    content: str
    visibility: str = "INTERNAL"


class SupportNoteResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    author_user_id: UUID
    visibility: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportTransitionRequest(BaseModel):
    new_state: str
    reason: str | None = None


class SupportEscalationCreate(BaseModel):
    reason: str
    new_severity: str
    escalated_to_user_id: UUID | None = None


class SupportEscalationResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    escalated_by_user_id: UUID
    escalated_to_user_id: UUID | None
    reason: str
    previous_severity: str
    new_severity: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportResolutionRequest(BaseModel):
    resolution_code: str
    summary: str | None = None


class SupportSLAEventResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    sla_type: str
    deadline_at: datetime | None
    actual_at: datetime | None
    is_breached: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportResolutionEventResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    event_type: str
    actor_user_id: UUID
    resolution_code: str | None
    summary: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupportStateTransitionResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    from_state: str
    to_state: str
    actor_user_id: UUID
    reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5: TRAINING & ENABLEMENT
# ═══════════════════════════════════════════════════════════════════════════════


class TrainingTrackCreate(BaseModel):
    name: str
    description: str
    target_role: str
    module_type: str = "REQUIRED"
    sort_order: int = 0
    is_active: bool = True
    curriculum: list = Field(default_factory=list)
    estimated_duration_minutes: int = 60


class TrainingTrackUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    curriculum: list | None = None
    estimated_duration_minutes: int | None = None


class TrainingTrackResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str
    target_role: str
    module_type: str
    sort_order: int
    is_active: bool
    curriculum: dict
    estimated_duration_minutes: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingAssignmentCreate(BaseModel):
    track_id: UUID
    user_id: UUID
    due_date: datetime


class TrainingAssignmentUpdate(BaseModel):
    status: str | None = None
    progress_pct: int | None = None
    due_date: datetime | None = None


class TrainingAssignmentResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    track_id: UUID
    user_id: UUID
    status: str
    assigned_by_user_id: UUID
    due_date: datetime
    started_at: datetime | None
    progress_pct: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingCompletionCreate(BaseModel):
    module_key: str
    score: float | None = None
    evidence: dict = Field(default_factory=dict)


class TrainingCompletionResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    module_key: str
    completed_at: datetime
    score: float | None
    evidence: dict

    model_config = ConfigDict(from_attributes=True)


class TrainingVerificationCreate(BaseModel):
    is_verified: bool
    notes: str | None = None


class TrainingVerificationResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    verifier_user_id: UUID
    is_verified: bool
    notes: str | None
    verified_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6: ADOPTION & HEALTH
# ═══════════════════════════════════════════════════════════════════════════════


class AccountHealthSnapshotResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    overall_state: str
    overall_score: float
    login_score: float
    adoption_score: float
    support_score: float
    training_score: float
    stability_score: float
    factor_breakdown: dict
    computation_log: dict
    snapshot_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdoptionMetricResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    category: str
    module_name: str
    metric_value: float
    active_user_count: int
    total_user_count: int
    period_start: datetime
    period_end: datetime
    detail: dict
    measured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowAdoptionMetricResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    workflow_name: str
    domain: str
    total_invocations: int
    successful_completions: int
    abandonment_count: int
    average_completion_seconds: float | None
    period_start: datetime
    period_end: datetime
    measured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SuccessRiskFactorResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    health_snapshot_id: UUID
    factor_name: str
    factor_category: str
    severity: str
    impact_score: float
    description: str
    recommended_action: str
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpansionReadinessSignalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    signal_type: str
    module_name: str | None
    signal_strength: float
    evidence: dict
    is_active: bool
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7: RENEWAL & EXPANSION
# ═══════════════════════════════════════════════════════════════════════════════


class RenewalRiskSignalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    risk_category: str
    severity: str
    title: str
    description: str
    source_factors: dict
    is_active: bool
    resolved_at: datetime | None
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpansionOpportunityCreate(BaseModel):
    module_name: str
    opportunity_type: str
    recommended_action: str
    evidence: dict = Field(default_factory=dict)
    estimated_value_cents: int | None = None


class ExpansionOpportunityUpdate(BaseModel):
    state: str | None = None
    assigned_to_user_id: UUID | None = None


class ExpansionOpportunityResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    module_name: str
    opportunity_type: str
    state: str
    evidence: dict
    estimated_value_cents: int | None
    recommended_action: str
    assigned_to_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StakeholderEngagementNoteCreate(BaseModel):
    stakeholder_name: str
    stakeholder_role: str
    engagement_type: str
    content: str
    sentiment: str | None = None


class StakeholderEngagementNoteResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    stakeholder_name: str
    stakeholder_role: str
    engagement_type: str
    content: str
    sentiment: str | None
    author_user_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ValueMilestoneCreate(BaseModel):
    milestone_name: str
    category: str
    description: str
    evidence: dict = Field(default_factory=dict)
    impact_summary: str | None = None


class ValueMilestoneUpdate(BaseModel):
    is_achieved: bool | None = None
    evidence: dict | None = None
    impact_summary: str | None = None


class ValueMilestoneResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    milestone_name: str
    category: str
    description: str
    is_achieved: bool
    achieved_at: datetime | None
    evidence: dict
    impact_summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 8: FOUNDER SUCCESS COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════════


class SuccessAction(BaseModel):
    domain: str
    severity: str
    summary: str
    recommended_action: str
    entity_id: UUID | None = None


class FounderSuccessSummary(BaseModel):
    stalled_implementations: int
    high_severity_tickets: int
    at_risk_accounts: int
    training_gaps: int
    low_adoption_modules: int
    expansion_ready_signals: int
    top_actions: list[SuccessAction]


class ImplementationHealthScore(BaseModel):
    total_projects: int
    on_track_pct: float
    at_risk_pct: float
    avg_milestone_completion_pct: float


class SupportQueueHealth(BaseModel):
    total_open: int
    critical_count: int
    high_count: int
    avg_age_hours: float
    sla_breach_count: int


class TrainingCompletionSummary(BaseModel):
    total_assignments: int
    completed_pct: float
    overdue_count: int
    verified_count: int


class AdoptionScoreSummary(BaseModel):
    overall_score: float
    module_scores: list[ModuleAdoptionScore]


class ModuleAdoptionScore(BaseModel):
    module_name: str
    adoption_pct: float
    active_users: int
    total_users: int


class ExpansionReadinessSummary(BaseModel):
    expansion_ready_count: int
    renewal_risk_count: int
    signals: list[ExpansionReadinessSignalResponse]


class SuccessAuditEventResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    project_id: UUID | None
    entity_type: str
    entity_id: UUID
    actor_user_id: UUID
    action: str
    detail: dict
    correlation_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
