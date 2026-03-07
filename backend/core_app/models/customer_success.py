"""
Customer Success Platform Models — Implementation Services, Support Operations,
Training & Enablement, Adoption & Health, Renewal & Expansion, Founder Success.

All models are tenant-scoped via TenantScopedMixin with UUID primary keys
following the established FusionEMS-Core pattern.
"""
# pylint: disable=not-callable,unsubscriptable-object
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin

# ══════════════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ══════════════════════════════════════════════════════════════════════════════


# ── Part 3: Implementation Services ──────────────────────────────────────────

class ImplementationState(StrEnum):
    PROJECT_CREATED = "PROJECT_CREATED"
    DISCOVERY = "DISCOVERY"
    CONFIGURATION = "CONFIGURATION"
    TRAINING = "TRAINING"
    READY_FOR_GO_LIVE = "READY_FOR_GO_LIVE"
    LIVE_STABILIZATION = "LIVE_STABILIZATION"
    HANDOFF_COMPLETE = "HANDOFF_COMPLETE"
    STALLED = "STALLED"
    ESCALATED = "ESCALATED"


class MilestoneStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    OVERDUE = "OVERDUE"
    SKIPPED = "SKIPPED"


class RiskSeverity(StrEnum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


# ── Part 4: Support Operations ───────────────────────────────────────────────

class SupportTicketState(StrEnum):
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_ON_CUSTOMER = "WAITING_ON_CUSTOMER"
    WAITING_ON_INTERNAL = "WAITING_ON_INTERNAL"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class SupportSeverityLevel(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SupportNoteVisibility(StrEnum):
    INTERNAL = "INTERNAL"
    CUSTOMER_VISIBLE = "CUSTOMER_VISIBLE"


class SupportResolutionCode(StrEnum):
    FIXED = "FIXED"
    WORKAROUND = "WORKAROUND"
    CANNOT_REPRODUCE = "CANNOT_REPRODUCE"
    DUPLICATE = "DUPLICATE"
    BY_DESIGN = "BY_DESIGN"
    CUSTOMER_EDUCATION = "CUSTOMER_EDUCATION"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    ESCALATED_TO_ENGINEERING = "ESCALATED_TO_ENGINEERING"
    NO_ACTION_REQUIRED = "NO_ACTION_REQUIRED"


# ── Part 5: Training & Enablement ────────────────────────────────────────────

class TrainingState(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"
    OVERDUE = "OVERDUE"
    REASSIGN_RECOMMENDED = "REASSIGN_RECOMMENDED"


class TrainingRole(StrEnum):
    ADMIN = "ADMIN"
    CREW = "CREW"
    DISPATCH = "DISPATCH"
    BILLER = "BILLER"
    CLINICAL_PROVIDER = "CLINICAL_PROVIDER"
    SUPERVISOR = "SUPERVISOR"


class TrainingModuleType(StrEnum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    RECOMMENDED = "RECOMMENDED"


# ── Part 6: Adoption & Health ────────────────────────────────────────────────

class AccountHealthState(StrEnum):
    HEALTHY = "HEALTHY"
    WATCH = "WATCH"
    AT_RISK = "AT_RISK"
    CRITICAL = "CRITICAL"
    EXPANSION_READY = "EXPANSION_READY"


class AdoptionMetricCategory(StrEnum):
    LOGIN_FREQUENCY = "LOGIN_FREQUENCY"
    MODULE_USAGE = "MODULE_USAGE"
    WORKFLOW_COMPLETION = "WORKFLOW_COMPLETION"
    FEATURE_DEPTH = "FEATURE_DEPTH"
    ACTIVE_USERS = "ACTIVE_USERS"


# ── Part 7: Renewal & Expansion ──────────────────────────────────────────────

class RenewalState(StrEnum):
    TOO_EARLY = "TOO_EARLY"
    UNDER_REVIEW = "UNDER_REVIEW"
    EXPANSION_READY = "EXPANSION_READY"
    RENEWAL_RISK = "RENEWAL_RISK"
    ESCALATED = "ESCALATED"


# ══════════════════════════════════════════════════════════════════════════════
# PART 3: IMPLEMENTATION SERVICES
# ══════════════════════════════════════════════════════════════════════════════


class CSImplementationProject(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Top-level implementation project per tenant onboarding."""
    __tablename__ = "cs_implementation_projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ImplementationState.PROJECT_CREATED.value, index=True
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_go_live_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_go_live_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stabilization_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    handoff_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    project_plan: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    go_live_criteria: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    milestones: Mapped[list[ImplementationMilestone]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    risk_flags: Mapped[list[ImplementationRiskFlag]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    stabilization_checkpoints: Mapped[list[StabilizationCheckpoint]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[SuccessAuditEvent]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ImplementationMilestone(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Individual onboarding milestone with owner, due date, and status."""
    __tablename__ = "cs_implementation_milestones"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_implementation_projects.id"),
        nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MilestoneStatus.NOT_STARTED.value
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checklist_items: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    dependencies: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    project: Mapped[CSImplementationProject] = relationship(back_populates="milestones")
    training_links: Mapped[list[ImplementationTrainingLink]] = relationship(
        back_populates="milestone", cascade="all, delete-orphan"
    )


class ImplementationTrainingLink(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Links an implementation milestone to a training assignment for tracking."""
    __tablename__ = "cs_implementation_training_links"

    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_implementation_milestones.id"),
        nullable=False, index=True
    )
    training_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_training_assignments.id"),
        nullable=False, index=True
    )
    is_blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    milestone: Mapped[ImplementationMilestone] = relationship(back_populates="training_links")
    training_assignment: Mapped[TrainingAssignment] = relationship(
        back_populates="implementation_links"
    )


class ImplementationRiskFlag(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Risk flags for at-risk or stalled implementations."""
    __tablename__ = "cs_implementation_risk_flags"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_implementation_projects.id"),
        nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    project: Mapped[CSImplementationProject] = relationship(back_populates="risk_flags")


class StabilizationCheckpoint(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Post-launch stabilization checkpoint during the stabilization window."""
    __tablename__ = "cs_stabilization_checkpoints"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_implementation_projects.id"),
        nullable=False, index=True
    )
    checkpoint_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checked_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    findings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[CSImplementationProject] = relationship(
        back_populates="stabilization_checkpoints"
    )


class SuccessAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Audit trail for all customer-success domain mutations."""
    __tablename__ = "cs_success_audit_events"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_implementation_projects.id"),
        nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[CSImplementationProject | None] = relationship(
        back_populates="audit_events"
    )


# ══════════════════════════════════════════════════════════════════════════════
# PART 4: SUPPORT OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════


class SupportTicket(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Full support ticket with severity, state machine, and context links."""
    __tablename__ = "cs_support_tickets"

    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=SupportTicketState.NEW.value, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SupportSeverityLevel.MEDIUM.value, index=True
    )
    reporter_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    linked_workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    linked_incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    linked_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    context_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    resolution_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reopened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_response_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_resolution_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    notes: Mapped[list[SupportNote]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    escalations: Mapped[list[SupportEscalation]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    sla_events: Mapped[list[SupportSLAEvent]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    resolution_events: Mapped[list[SupportResolutionEvent]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    state_transitions: Mapped[list[SupportStateTransition]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class SupportNote(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Internal or customer-visible note on a support ticket."""
    __tablename__ = "cs_support_notes"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_support_tickets.id"),
        nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SupportNoteVisibility.INTERNAL.value
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped[SupportTicket] = relationship(back_populates="notes")


class SupportEscalation(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Escalation event on a support ticket."""
    __tablename__ = "cs_support_escalations"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_support_tickets.id"),
        nullable=False, index=True
    )
    escalated_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    escalated_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_severity: Mapped[str] = mapped_column(String(20), nullable=False)
    new_severity: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped[SupportTicket] = relationship(back_populates="escalations")


class SupportSLAEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """SLA timer event tracking response/resolution deadlines and breaches."""
    __tablename__ = "cs_support_sla_events"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_support_tickets.id"),
        nullable=False, index=True
    )
    sla_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # RESPONSE_DUE, RESOLUTION_DUE, RESPONSE_MET, RESPONSE_BREACHED, etc.
    deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_breached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped[SupportTicket] = relationship(back_populates="sla_events")


class SupportResolutionEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Resolution or reopen event on a support ticket."""
    __tablename__ = "cs_support_resolution_events"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_support_tickets.id"),
        nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # RESOLVED, CLOSED, REOPENED
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resolution_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped[SupportTicket] = relationship(back_populates="resolution_events")


class SupportStateTransition(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Auditable state transition log for support ticket status changes."""
    __tablename__ = "cs_support_state_transitions"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_support_tickets.id"),
        nullable=False, index=True
    )
    from_state: Mapped[str] = mapped_column(String(30), nullable=False)
    to_state: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped[SupportTicket] = relationship(back_populates="state_transitions")


# ══════════════════════════════════════════════════════════════════════════════
# PART 5: TRAINING & ENABLEMENT
# ══════════════════════════════════════════════════════════════════════════════


class TrainingTrack(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Role-based training curriculum track."""
    __tablename__ = "cs_training_tracks"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    module_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=TrainingModuleType.REQUIRED.value
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    curriculum: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    assignments: Mapped[list[TrainingAssignment]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )


class TrainingAssignment(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Assignment of a training track to a specific user."""
    __tablename__ = "cs_training_assignments"

    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_training_tracks.id"),
        nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=TrainingState.NOT_STARTED.value, index=True
    )
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    track: Mapped[TrainingTrack] = relationship(back_populates="assignments")
    completions: Mapped[list[TrainingCompletion]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )
    verifications: Mapped[list[TrainingVerification]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )
    implementation_links: Mapped[list[ImplementationTrainingLink]] = relationship(
        back_populates="training_assignment", cascade="all, delete-orphan"
    )


class TrainingCompletion(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Completion record for individual training modules within an assignment."""
    __tablename__ = "cs_training_completions"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_training_assignments.id"),
        nullable=False, index=True
    )
    module_key: Mapped[str] = mapped_column(String(100), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    assignment: Mapped[TrainingAssignment] = relationship(back_populates="completions")


class TrainingVerification(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Verification / sign-off by supervisor confirming competency."""
    __tablename__ = "cs_training_verifications"

    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_training_assignments.id"),
        nullable=False, index=True
    )
    verifier_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assignment: Mapped[TrainingAssignment] = relationship(back_populates="verifications")


class EnablementAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Audit trail for training / enablement mutations."""
    __tablename__ = "cs_enablement_audit_events"

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ══════════════════════════════════════════════════════════════════════════════
# PART 6: ADOPTION & HEALTH
# ══════════════════════════════════════════════════════════════════════════════


class AccountHealthSnapshot(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Point-in-time account health assessment with multi-factor scoring."""
    __tablename__ = "cs_account_health_snapshots"

    overall_state: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    login_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    adoption_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    support_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    training_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    factor_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    computation_log: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    risk_factors: Mapped[list[SuccessRiskFactor]] = relationship(
        back_populates="health_snapshot", cascade="all, delete-orphan"
    )


class AdoptionMetric(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Per-module, per-tenant adoption metric snapshot."""
    __tablename__ = "cs_adoption_metrics"

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    active_user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_user_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WorkflowAdoptionMetric(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Tracks critical workflow adoption depth per tenant."""
    __tablename__ = "cs_workflow_adoption_metrics"

    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    total_invocations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_completions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    abandonment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_completion_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SuccessRiskFactor(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Individual risk factor contributing to account health score."""
    __tablename__ = "cs_success_risk_factors"

    health_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_account_health_snapshots.id"),
        nullable=False, index=True
    )
    factor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    factor_category: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    impact_score: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    health_snapshot: Mapped[AccountHealthSnapshot] = relationship(
        back_populates="risk_factors"
    )


class ExpansionReadinessSignal(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Signal indicating a tenant is ready for expansion based on usage patterns."""
    __tablename__ = "cs_expansion_readiness_signals"

    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    module_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    signal_strength: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ══════════════════════════════════════════════════════════════════════════════
# PART 7: RENEWAL & EXPANSION
# ══════════════════════════════════════════════════════════════════════════════


class RenewalRiskSignal(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Signal indicating renewal risk for a tenant account."""
    __tablename__ = "cs_renewal_risk_signals"

    risk_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_factors: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExpansionOpportunity(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Module-fit expansion opportunity grounded in actual usage data."""
    __tablename__ = "cs_expansion_opportunities"

    module_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    opportunity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RenewalState.TOO_EARLY.value, index=True
    )
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    estimated_value_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )


class StakeholderEngagementNote(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Notes on stakeholder engagement and relationship health."""
    __tablename__ = "cs_stakeholder_engagement_notes"

    stakeholder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stakeholder_role: Mapped[str] = mapped_column(String(100), nullable=False)
    engagement_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ValueMilestone(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    """Value-realization milestone that demonstrates ROI to the customer."""
    __tablename__ = "cs_value_milestones"

    milestone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_achieved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    achieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


# ══════════════════════════════════════════════════════════════════════════════
# PART 10-11: HARDENING — MILESTONE AUDIT LOG + HEALTH COMPUTATION LOG
# ══════════════════════════════════════════════════════════════════════════════


class MilestoneUpdateLog(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Auditable log of all milestone status changes."""
    __tablename__ = "cs_milestone_update_logs"

    milestone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_implementation_milestones.id"),
        nullable=False, index=True
    )
    previous_status: Mapped[str] = mapped_column(String(20), nullable=False)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class HealthComputationLog(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    """Audit log of when/why account health scores are computed and changed."""
    __tablename__ = "cs_health_computation_logs"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cs_account_health_snapshots.id"),
        nullable=False, index=True
    )
    trigger: Mapped[str] = mapped_column(String(100), nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_state: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_score: Mapped[float] = mapped_column(Float, nullable=False)
    computation_detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
