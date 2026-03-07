"""
Customer Success Service — Implementation Services, Support Operations,
Training & Enablement, Adoption & Health, Renewal & Expansion.

All mutations are auditable, tenant-scoped, and follow the FusionEMS-Core
service-layer pattern (sync SQLAlchemy session, explicit error taxonomy).
"""
# pylint: disable=not-callable
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.customer_success import (
    AccountHealthSnapshot,
    AccountHealthState,
    AdoptionMetric,
    CSImplementationProject,
    EnablementAuditEvent,
    ExpansionOpportunity,
    ExpansionReadinessSignal,
    HealthComputationLog,
    ImplementationMilestone,
    ImplementationRiskFlag,
    ImplementationState,
    MilestoneStatus,
    MilestoneUpdateLog,
    RenewalRiskSignal,
    StabilizationCheckpoint,
    StakeholderEngagementNote,
    SuccessAuditEvent,
    SuccessRiskFactor,
    SupportEscalation,
    SupportNote,
    SupportResolutionEvent,
    SupportSeverityLevel,
    SupportSLAEvent,
    SupportStateTransition,
    SupportTicket,
    SupportTicketState,
    TrainingAssignment,
    TrainingCompletion,
    TrainingState,
    TrainingTrack,
    TrainingVerification,
    ValueMilestone,
    WorkflowAdoptionMetric,
)

# SLA targets in hours by severity
_SLA_RESPONSE_HOURS: dict[str, int] = {
    SupportSeverityLevel.CRITICAL: 1,
    SupportSeverityLevel.HIGH: 4,
    SupportSeverityLevel.MEDIUM: 8,
    SupportSeverityLevel.LOW: 24,
}
_SLA_RESOLUTION_HOURS: dict[str, int] = {
    SupportSeverityLevel.CRITICAL: 4,
    SupportSeverityLevel.HIGH: 24,
    SupportSeverityLevel.MEDIUM: 72,
    SupportSeverityLevel.LOW: 168,
}

# Valid support state transitions
_SUPPORT_TRANSITIONS: dict[str, set[str]] = {
    SupportTicketState.NEW: {
        SupportTicketState.TRIAGED, SupportTicketState.ASSIGNED,
        SupportTicketState.ESCALATED,
    },
    SupportTicketState.TRIAGED: {
        SupportTicketState.ASSIGNED, SupportTicketState.ESCALATED,
    },
    SupportTicketState.ASSIGNED: {
        SupportTicketState.IN_PROGRESS, SupportTicketState.ESCALATED,
        SupportTicketState.WAITING_ON_CUSTOMER, SupportTicketState.WAITING_ON_INTERNAL,
    },
    SupportTicketState.IN_PROGRESS: {
        SupportTicketState.WAITING_ON_CUSTOMER, SupportTicketState.WAITING_ON_INTERNAL,
        SupportTicketState.ESCALATED, SupportTicketState.RESOLVED,
    },
    SupportTicketState.WAITING_ON_CUSTOMER: {
        SupportTicketState.IN_PROGRESS, SupportTicketState.RESOLVED,
        SupportTicketState.CLOSED,
    },
    SupportTicketState.WAITING_ON_INTERNAL: {
        SupportTicketState.IN_PROGRESS, SupportTicketState.ESCALATED,
    },
    SupportTicketState.ESCALATED: {
        SupportTicketState.ASSIGNED, SupportTicketState.IN_PROGRESS,
    },
    SupportTicketState.RESOLVED: {
        SupportTicketState.CLOSED, SupportTicketState.REOPENED,
    },
    SupportTicketState.CLOSED: {
        SupportTicketState.REOPENED,
    },
    SupportTicketState.REOPENED: {
        SupportTicketState.TRIAGED, SupportTicketState.ASSIGNED,
        SupportTicketState.IN_PROGRESS,
    },
}


class CustomerSuccessService:
    """Unified service for all customer-success domain operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _audit(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        detail: dict | None = None,
        project_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
    ) -> SuccessAuditEvent:
        evt = SuccessAuditEvent(
            tenant_id=tenant_id,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            action=action,
            detail=detail or {},
            correlation_id=correlation_id,
        )
        self.db.add(evt)
        return evt

    def _enablement_audit(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        detail: dict | None = None,
    ) -> EnablementAuditEvent:
        evt = EnablementAuditEvent(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            action=action,
            detail=detail or {},
        )
        self.db.add(evt)
        return evt

    # ══════════════════════════════════════════════════════════════════════════
    # PART 3: IMPLEMENTATION SERVICES
    # ══════════════════════════════════════════════════════════════════════════

    def create_implementation_project(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        owner_user_id: uuid.UUID,
        target_go_live_date: datetime | None = None,
        project_plan: dict | None = None,
        go_live_criteria: dict | None = None,
        notes: str | None = None,
    ) -> CSImplementationProject:
        project = CSImplementationProject(
            tenant_id=tenant_id,
            name=name,
            owner_user_id=owner_user_id,
            target_go_live_date=target_go_live_date,
            project_plan=project_plan or {},
            go_live_criteria=go_live_criteria or {},
            notes=notes,
        )
        self.db.add(project)
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "CSImplementationProject", project.id,
            "CREATED", {"name": name}, project_id=project.id,
        )
        return project

    def get_implementation_project(
        self, tenant_id: uuid.UUID, project_id: uuid.UUID
    ) -> CSImplementationProject:
        stmt = select(CSImplementationProject).where(
            CSImplementationProject.tenant_id == tenant_id,
            CSImplementationProject.id == project_id,
        )
        project = self.db.execute(stmt).scalar_one_or_none()
        if project is None:
            raise AppError(code="NOT_FOUND", message="Implementation project not found", status_code=404)
        return project

    def list_implementation_projects(
        self, tenant_id: uuid.UUID, state: str | None = None
    ) -> list[CSImplementationProject]:
        stmt = select(CSImplementationProject).where(
            CSImplementationProject.tenant_id == tenant_id
        ).order_by(CSImplementationProject.created_at.desc())
        if state:
            stmt = stmt.where(CSImplementationProject.state == state)
        return list(self.db.execute(stmt).scalars().all())

    def transition_project_state(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        project_id: uuid.UUID,
        new_state: str,
        reason: str | None = None,
    ) -> CSImplementationProject:
        project = self.get_implementation_project(tenant_id, project_id)
        old_state = project.state
        # Validate new_state is a valid ImplementationState
        try:
            ImplementationState(new_state)
        except ValueError as exc:
            raise AppError(code="VALIDATION_ERROR", message=f"Invalid implementation state: {new_state}", status_code=400) from exc
        project.state = new_state
        if new_state == ImplementationState.HANDOFF_COMPLETE:
            project.handoff_completed_at = datetime.now(UTC)
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "CSImplementationProject", project.id,
            "STATE_CHANGED", {"from": old_state, "to": new_state, "reason": reason},
            project_id=project.id,
        )
        return project

    def update_implementation_project(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        project_id: uuid.UUID,
        **kwargs: Any,
    ) -> CSImplementationProject:
        project = self.get_implementation_project(tenant_id, project_id)
        changes: dict[str, Any] = {}
        for field in (
            "name", "target_go_live_date", "actual_go_live_date",
            "stabilization_end_date", "project_plan", "go_live_criteria", "notes",
        ):
            if field in kwargs and kwargs[field] is not None:
                old = getattr(project, field)
                setattr(project, field, kwargs[field])
                changes[field] = {"from": str(old), "to": str(kwargs[field])}
        if kwargs.get("state"):
            return self.transition_project_state(
                tenant_id, actor_user_id, project_id, kwargs["state"],
            )
        self.db.flush()
        if changes:
            self._audit(
                tenant_id, actor_user_id, "CSImplementationProject", project.id,
                "UPDATED", changes, project_id=project.id,
            )
        return project

    # ── Milestones ────────────────────────────────────────────────────────────

    def create_milestone(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str,
        description: str,
        owner_user_id: uuid.UUID,
        due_date: datetime,
        sort_order: int = 0,
        checklist_items: list | None = None,
        dependencies: list | None = None,
    ) -> ImplementationMilestone:
        self.get_implementation_project(tenant_id, project_id)  # verify exists
        milestone = ImplementationMilestone(
            tenant_id=tenant_id,
            project_id=project_id,
            name=name,
            description=description,
            owner_user_id=owner_user_id,
            due_date=due_date,
            sort_order=sort_order,
            checklist_items=checklist_items or [],
            dependencies=dependencies or [],
        )
        self.db.add(milestone)
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "ImplementationMilestone", milestone.id,
            "CREATED", {"name": name}, project_id=project_id,
        )
        return milestone

    def update_milestone_status(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        milestone_id: uuid.UUID,
        new_status: str,
        reason: str | None = None,
    ) -> ImplementationMilestone:
        stmt = select(ImplementationMilestone).where(
            ImplementationMilestone.tenant_id == tenant_id,
            ImplementationMilestone.id == milestone_id,
        )
        milestone = self.db.execute(stmt).scalar_one_or_none()
        if milestone is None:
            raise AppError(code="NOT_FOUND", message="Milestone not found", status_code=404)
        try:
            MilestoneStatus(new_status)
        except ValueError as exc:
            raise AppError(code="VALIDATION_ERROR", message=f"Invalid milestone status: {new_status}", status_code=400) from exc
        old_status = milestone.status
        milestone.status = new_status
        if new_status == MilestoneStatus.COMPLETED:
            milestone.completed_at = datetime.now(UTC)
        self.db.flush()
        # Milestone update log (hardening)
        log = MilestoneUpdateLog(
            tenant_id=tenant_id,
            milestone_id=milestone.id,
            previous_status=old_status,
            new_status=new_status,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        self.db.add(log)
        self._audit(
            tenant_id, actor_user_id, "ImplementationMilestone", milestone.id,
            "STATUS_CHANGED", {"from": old_status, "to": new_status, "reason": reason},
            project_id=milestone.project_id,
        )
        self.db.flush()
        return milestone

    def list_milestones(
        self, tenant_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[ImplementationMilestone]:
        stmt = (
            select(ImplementationMilestone)
            .where(
                ImplementationMilestone.tenant_id == tenant_id,
                ImplementationMilestone.project_id == project_id,
            )
            .order_by(ImplementationMilestone.sort_order)
        )
        return list(self.db.execute(stmt).scalars().all())

    # ── Risk Flags ────────────────────────────────────────────────────────────

    def add_risk_flag(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        project_id: uuid.UUID,
        title: str,
        description: str,
        severity: str,
        source: str = "MANUAL",
    ) -> ImplementationRiskFlag:
        self.get_implementation_project(tenant_id, project_id)
        flag = ImplementationRiskFlag(
            tenant_id=tenant_id,
            project_id=project_id,
            severity=severity,
            title=title,
            description=description,
            source=source,
        )
        self.db.add(flag)
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "ImplementationRiskFlag", flag.id,
            "CREATED", {"title": title, "severity": severity},
            project_id=project_id,
        )
        return flag

    def resolve_risk_flag(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        flag_id: uuid.UUID,
    ) -> ImplementationRiskFlag:
        stmt = select(ImplementationRiskFlag).where(
            ImplementationRiskFlag.tenant_id == tenant_id,
            ImplementationRiskFlag.id == flag_id,
        )
        flag = self.db.execute(stmt).scalar_one_or_none()
        if flag is None:
            raise AppError(code="NOT_FOUND", message="Risk flag not found", status_code=404)
        flag.is_resolved = True
        flag.resolved_at = datetime.now(UTC)
        flag.resolved_by_user_id = actor_user_id
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "ImplementationRiskFlag", flag.id,
            "RESOLVED", {}, project_id=flag.project_id,
        )
        return flag

    # ── Stabilization Checkpoints ─────────────────────────────────────────────

    def add_stabilization_checkpoint(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        project_id: uuid.UUID,
        checkpoint_name: str,
        is_passed: bool,
        findings: dict | None = None,
    ) -> StabilizationCheckpoint:
        self.get_implementation_project(tenant_id, project_id)
        cp = StabilizationCheckpoint(
            tenant_id=tenant_id,
            project_id=project_id,
            checkpoint_name=checkpoint_name,
            checked_by_user_id=actor_user_id,
            is_passed=is_passed,
            findings=findings or {},
        )
        self.db.add(cp)
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "StabilizationCheckpoint", cp.id,
            "CREATED", {"name": checkpoint_name, "passed": is_passed},
            project_id=project_id,
        )
        return cp

    # ── Go-Live Approval ──────────────────────────────────────────────────────

    def approve_go_live(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        project_id: uuid.UUID,
        approved: bool,
        reason: str,
    ) -> CSImplementationProject:
        project = self.get_implementation_project(tenant_id, project_id)
        if project.state != ImplementationState.READY_FOR_GO_LIVE:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Project must be in READY_FOR_GO_LIVE state, currently {project.state}",
                status_code=400,
            )
        if approved:
            project.state = ImplementationState.LIVE_STABILIZATION
            project.actual_go_live_date = datetime.now(UTC)
        else:
            project.state = ImplementationState.CONFIGURATION
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "CSImplementationProject", project.id,
            "GO_LIVE_DECISION", {"approved": approved, "reason": reason},
            project_id=project.id,
        )
        return project

    # ══════════════════════════════════════════════════════════════════════════
    # PART 4: SUPPORT OPERATIONS
    # ══════════════════════════════════════════════════════════════════════════

    def create_support_ticket(
        self,
        tenant_id: uuid.UUID,
        reporter_user_id: uuid.UUID,
        subject: str,
        description: str,
        severity: str = SupportSeverityLevel.MEDIUM,
        category: str | None = None,
        linked_workflow_id: uuid.UUID | None = None,
        linked_incident_id: uuid.UUID | None = None,
        linked_claim_id: uuid.UUID | None = None,
        context_metadata: dict | None = None,
    ) -> SupportTicket:
        try:
            SupportSeverityLevel(severity)
        except ValueError as exc:
            raise AppError(code="VALIDATION_ERROR", message=f"Invalid severity: {severity}", status_code=400) from exc
        now = datetime.now(UTC)
        response_hours = _SLA_RESPONSE_HOURS.get(severity, 8)
        resolution_hours = _SLA_RESOLUTION_HOURS.get(severity, 72)
        ticket = SupportTicket(
            tenant_id=tenant_id,
            subject=subject,
            description=description,
            severity=severity,
            reporter_user_id=reporter_user_id,
            category=category,
            linked_workflow_id=linked_workflow_id,
            linked_incident_id=linked_incident_id,
            linked_claim_id=linked_claim_id,
            context_metadata=context_metadata or {},
            sla_response_due_at=now + timedelta(hours=response_hours),
            sla_resolution_due_at=now + timedelta(hours=resolution_hours),
        )
        self.db.add(ticket)
        self.db.flush()
        # Record SLA events
        for sla_type, deadline in [
            ("RESPONSE_DUE", ticket.sla_response_due_at),
            ("RESOLUTION_DUE", ticket.sla_resolution_due_at),
        ]:
            sla = SupportSLAEvent(
                tenant_id=tenant_id,
                ticket_id=ticket.id,
                sla_type=sla_type,
                deadline_at=deadline,
            )
            self.db.add(sla)
        self._audit(
            tenant_id, reporter_user_id, "SupportTicket", ticket.id,
            "CREATED", {"subject": subject, "severity": severity},
        )
        self.db.flush()
        return ticket

    def get_support_ticket(
        self, tenant_id: uuid.UUID, ticket_id: uuid.UUID
    ) -> SupportTicket:
        stmt = select(SupportTicket).where(
            SupportTicket.tenant_id == tenant_id,
            SupportTicket.id == ticket_id,
        )
        ticket = self.db.execute(stmt).scalar_one_or_none()
        if ticket is None:
            raise AppError(code="NOT_FOUND", message="Support ticket not found", status_code=404)
        return ticket

    def list_support_tickets(
        self,
        tenant_id: uuid.UUID,
        status: str | None = None,
        severity: str | None = None,
        assigned_to: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SupportTicket]:
        stmt = select(SupportTicket).where(
            SupportTicket.tenant_id == tenant_id
        ).order_by(SupportTicket.created_at.desc())
        if status:
            stmt = stmt.where(SupportTicket.status == status)
        if severity:
            stmt = stmt.where(SupportTicket.severity == severity)
        if assigned_to:
            stmt = stmt.where(SupportTicket.assigned_to_user_id == assigned_to)
        stmt = stmt.limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def transition_support_ticket(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ticket_id: uuid.UUID,
        new_state: str,
        reason: str | None = None,
    ) -> SupportTicket:
        ticket = self.get_support_ticket(tenant_id, ticket_id)
        try:
            SupportTicketState(new_state)
        except ValueError as exc:
            raise AppError(code="VALIDATION_ERROR", message=f"Invalid ticket state: {new_state}", status_code=400) from exc
        allowed = _SUPPORT_TRANSITIONS.get(ticket.status, set())
        if new_state not in allowed:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Cannot transition from {ticket.status} to {new_state}",
                status_code=400,
            )
        old_state = ticket.status
        ticket.status = new_state
        now = datetime.now(UTC)
        if new_state == SupportTicketState.RESOLVED:
            ticket.resolved_at = now
        elif new_state == SupportTicketState.CLOSED:
            ticket.closed_at = now
        elif new_state == SupportTicketState.REOPENED:
            ticket.reopened_at = now
            ticket.resolved_at = None
            ticket.closed_at = None
        transition = SupportStateTransition(
            tenant_id=tenant_id,
            ticket_id=ticket.id,
            from_state=old_state,
            to_state=new_state,
            actor_user_id=actor_user_id,
            reason=reason,
        )
        self.db.add(transition)
        self._audit(
            tenant_id, actor_user_id, "SupportTicket", ticket.id,
            "STATE_CHANGED", {"from": old_state, "to": new_state, "reason": reason},
        )
        self.db.flush()
        return ticket

    def add_support_note(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ticket_id: uuid.UUID,
        content: str,
        visibility: str = "INTERNAL",
    ) -> SupportNote:
        self.get_support_ticket(tenant_id, ticket_id)
        note = SupportNote(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            author_user_id=actor_user_id,
            visibility=visibility,
            content=content,
        )
        self.db.add(note)
        self.db.flush()
        return note

    def escalate_ticket(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ticket_id: uuid.UUID,
        reason: str,
        new_severity: str,
        escalated_to_user_id: uuid.UUID | None = None,
    ) -> SupportEscalation:
        ticket = self.get_support_ticket(tenant_id, ticket_id)
        try:
            SupportSeverityLevel(new_severity)
        except ValueError as exc:
            raise AppError(code="VALIDATION_ERROR", message=f"Invalid severity: {new_severity}", status_code=400) from exc
        previous_severity = ticket.severity
        ticket.severity = new_severity
        if ticket.status != SupportTicketState.ESCALATED:
            self.transition_support_ticket(
                tenant_id, actor_user_id, ticket_id,
                SupportTicketState.ESCALATED, reason,
            )
        escalation = SupportEscalation(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            escalated_by_user_id=actor_user_id,
            escalated_to_user_id=escalated_to_user_id,
            reason=reason,
            previous_severity=previous_severity,
            new_severity=new_severity,
        )
        self.db.add(escalation)
        self.db.flush()
        return escalation

    def resolve_ticket(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ticket_id: uuid.UUID,
        resolution_code: str,
        summary: str | None = None,
    ) -> SupportTicket:
        ticket = self.get_support_ticket(tenant_id, ticket_id)
        ticket.resolution_code = resolution_code
        ticket.resolution_summary = summary
        self.transition_support_ticket(
            tenant_id, actor_user_id, ticket_id,
            SupportTicketState.RESOLVED, f"Resolved: {resolution_code}",
        )
        event = SupportResolutionEvent(
            tenant_id=tenant_id,
            ticket_id=ticket_id,
            event_type="RESOLVED",
            actor_user_id=actor_user_id,
            resolution_code=resolution_code,
            summary=summary,
        )
        self.db.add(event)
        # Check SLA met
        now = datetime.now(UTC)
        if ticket.sla_resolution_due_at and now <= ticket.sla_resolution_due_at:
            sla = SupportSLAEvent(
                tenant_id=tenant_id, ticket_id=ticket_id,
                sla_type="RESOLUTION_MET", actual_at=now, is_breached=False,
            )
        else:
            sla = SupportSLAEvent(
                tenant_id=tenant_id, ticket_id=ticket_id,
                sla_type="RESOLUTION_BREACHED", actual_at=now, is_breached=True,
            )
        self.db.add(sla)
        self.db.flush()
        return ticket

    def reopen_ticket(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ticket_id: uuid.UUID,
        reason: str,
    ) -> SupportTicket:
        ticket = self.transition_support_ticket(
            tenant_id, actor_user_id, ticket_id,
            SupportTicketState.REOPENED, reason,
        )
        event = SupportResolutionEvent(
            tenant_id=tenant_id,
            ticket_id=ticket.id,
            event_type="REOPENED",
            actor_user_id=actor_user_id,
            summary=reason,
        )
        self.db.add(event)
        self.db.flush()
        return ticket

    # ══════════════════════════════════════════════════════════════════════════
    # PART 5: TRAINING & ENABLEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def create_training_track(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        name: str,
        description: str,
        target_role: str,
        module_type: str = "REQUIRED",
        sort_order: int = 0,
        curriculum: list | None = None,
        estimated_duration_minutes: int = 60,
    ) -> TrainingTrack:
        track = TrainingTrack(
            tenant_id=tenant_id,
            name=name,
            description=description,
            target_role=target_role,
            module_type=module_type,
            sort_order=sort_order,
            curriculum=curriculum or [],
            estimated_duration_minutes=estimated_duration_minutes,
        )
        self.db.add(track)
        self.db.flush()
        self._enablement_audit(
            tenant_id, actor_user_id, "TrainingTrack", track.id,
            "CREATED", {"name": name, "role": target_role},
        )
        return track

    def list_training_tracks(
        self, tenant_id: uuid.UUID, role: str | None = None, active_only: bool = True
    ) -> list[TrainingTrack]:
        stmt = select(TrainingTrack).where(
            TrainingTrack.tenant_id == tenant_id
        ).order_by(TrainingTrack.sort_order)
        if role:
            stmt = stmt.where(TrainingTrack.target_role == role)
        if active_only:
            stmt = stmt.where(TrainingTrack.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def assign_training(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        track_id: uuid.UUID,
        user_id: uuid.UUID,
        due_date: datetime,
    ) -> TrainingAssignment:
        assignment = TrainingAssignment(
            tenant_id=tenant_id,
            track_id=track_id,
            user_id=user_id,
            assigned_by_user_id=actor_user_id,
            due_date=due_date,
        )
        self.db.add(assignment)
        self.db.flush()
        self._enablement_audit(
            tenant_id, actor_user_id, "TrainingAssignment", assignment.id,
            "ASSIGNED", {"track_id": str(track_id), "user_id": str(user_id)},
        )
        return assignment

    def update_training_assignment(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        assignment_id: uuid.UUID,
        status: str | None = None,
        progress_pct: int | None = None,
        due_date: datetime | None = None,
    ) -> TrainingAssignment:
        stmt = select(TrainingAssignment).where(
            TrainingAssignment.tenant_id == tenant_id,
            TrainingAssignment.id == assignment_id,
        )
        assignment = self.db.execute(stmt).scalar_one_or_none()
        if assignment is None:
            raise AppError(code="NOT_FOUND", message="Training assignment not found", status_code=404)
        changes: dict[str, Any] = {}
        if status is not None:
            try:
                TrainingState(status)
            except ValueError as exc:
                raise AppError(code="VALIDATION_ERROR", message=f"Invalid training state: {status}", status_code=400) from exc
            old = assignment.status
            assignment.status = status
            changes["status"] = {"from": old, "to": status}
            if status == TrainingState.IN_PROGRESS and assignment.started_at is None:
                assignment.started_at = datetime.now(UTC)
        if progress_pct is not None:
            assignment.progress_pct = progress_pct
            changes["progress_pct"] = progress_pct
        if due_date is not None:
            assignment.due_date = due_date
        self.db.flush()
        if changes:
            self._enablement_audit(
                tenant_id, actor_user_id, "TrainingAssignment", assignment.id,
                "UPDATED", changes,
            )
        return assignment

    def record_training_completion(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        assignment_id: uuid.UUID,
        module_key: str,
        score: float | None = None,
        evidence: dict | None = None,
    ) -> TrainingCompletion:
        stmt = select(TrainingAssignment).where(
            TrainingAssignment.tenant_id == tenant_id,
            TrainingAssignment.id == assignment_id,
        )
        assignment = self.db.execute(stmt).scalar_one_or_none()
        if assignment is None:
            raise AppError(code="NOT_FOUND", message="Training assignment not found", status_code=404)
        completion = TrainingCompletion(
            tenant_id=tenant_id,
            assignment_id=assignment_id,
            module_key=module_key,
            score=score,
            evidence=evidence or {},
        )
        self.db.add(completion)
        self.db.flush()
        self._enablement_audit(
            tenant_id, actor_user_id, "TrainingCompletion", completion.id,
            "MODULE_COMPLETED", {"module_key": module_key, "score": score},
        )
        return completion

    def verify_training(
        self,
        tenant_id: uuid.UUID,
        verifier_user_id: uuid.UUID,
        assignment_id: uuid.UUID,
        is_verified: bool,
        notes: str | None = None,
    ) -> TrainingVerification:
        stmt = select(TrainingAssignment).where(
            TrainingAssignment.tenant_id == tenant_id,
            TrainingAssignment.id == assignment_id,
        )
        assignment = self.db.execute(stmt).scalar_one_or_none()
        if assignment is None:
            raise AppError(code="NOT_FOUND", message="Training assignment not found", status_code=404)
        verification = TrainingVerification(
            tenant_id=tenant_id,
            assignment_id=assignment_id,
            verifier_user_id=verifier_user_id,
            is_verified=is_verified,
            notes=notes,
        )
        self.db.add(verification)
        if is_verified:
            assignment.status = TrainingState.VERIFIED
        self.db.flush()
        self._enablement_audit(
            tenant_id, verifier_user_id, "TrainingVerification", verification.id,
            "VERIFIED" if is_verified else "VERIFICATION_FAILED",
            {"assignment_id": str(assignment_id), "verified": is_verified},
        )
        return verification

    def list_training_assignments(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> list[TrainingAssignment]:
        stmt = select(TrainingAssignment).where(
            TrainingAssignment.tenant_id == tenant_id
        ).order_by(TrainingAssignment.due_date)
        if user_id:
            stmt = stmt.where(TrainingAssignment.user_id == user_id)
        if status:
            stmt = stmt.where(TrainingAssignment.status == status)
        return list(self.db.execute(stmt).scalars().all())

    # ══════════════════════════════════════════════════════════════════════════
    # PART 6: ADOPTION & HEALTH
    # ══════════════════════════════════════════════════════════════════════════

    def compute_account_health(
        self, tenant_id: uuid.UUID, trigger: str = "SCHEDULED"
    ) -> AccountHealthSnapshot:
        """Compute and persist an account health snapshot for a tenant."""
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)

        # Login/adoption score from adoption metrics
        adoption_stmt = select(AdoptionMetric).where(
            AdoptionMetric.tenant_id == tenant_id,
            AdoptionMetric.measured_at >= week_ago,
        )
        adoption_rows = list(self.db.execute(adoption_stmt).scalars().all())
        adoption_score = 0.0
        login_score = 0.0
        if adoption_rows:
            active_total = sum(r.active_user_count for r in adoption_rows)
            user_total = sum(r.total_user_count for r in adoption_rows) or 1
            adoption_score = min((active_total / user_total) * 100, 100.0)
            login_metrics = [r for r in adoption_rows if r.category == "LOGIN_FREQUENCY"]
            if login_metrics:
                login_score = min(sum(r.metric_value for r in login_metrics) / len(login_metrics), 100.0)
            else:
                login_score = adoption_score

        # Support score (inverse of issue burden)
        open_ticket_count = self.db.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.tenant_id == tenant_id,
                SupportTicket.status.notin_([
                    SupportTicketState.RESOLVED,
                    SupportTicketState.CLOSED,
                ]),
            )
        ).scalar_one()
        support_score = max(100.0 - (open_ticket_count * 10), 0.0)

        # Training score
        total_assignments = self.db.execute(
            select(func.count(TrainingAssignment.id)).where(
                TrainingAssignment.tenant_id == tenant_id,
            )
        ).scalar_one()
        completed_assignments = self.db.execute(
            select(func.count(TrainingAssignment.id)).where(
                TrainingAssignment.tenant_id == tenant_id,
                TrainingAssignment.status.in_([
                    TrainingState.COMPLETED, TrainingState.VERIFIED,
                ]),
            )
        ).scalar_one()
        training_score = (completed_assignments / max(total_assignments, 1)) * 100.0

        # Stability score (from implementation state)
        impl_stmt = select(CSImplementationProject).where(
            CSImplementationProject.tenant_id == tenant_id,
        ).order_by(CSImplementationProject.created_at.desc()).limit(1)
        impl = self.db.execute(impl_stmt).scalar_one_or_none()
        stability_score = 50.0
        if impl:
            stable_states = {
                ImplementationState.HANDOFF_COMPLETE,
                ImplementationState.LIVE_STABILIZATION,
            }
            if impl.state in stable_states:
                stability_score = 90.0
            elif impl.state == ImplementationState.STALLED:
                stability_score = 20.0
            elif impl.state == ImplementationState.ESCALATED:
                stability_score = 30.0
            else:
                stability_score = 60.0

        # Overall score is a weighted average
        overall_score = (
            login_score * 0.15
            + adoption_score * 0.25
            + support_score * 0.20
            + training_score * 0.20
            + stability_score * 0.20
        )

        # Determine state
        if overall_score >= 80:
            state = AccountHealthState.HEALTHY
        elif overall_score >= 60:
            state = AccountHealthState.WATCH
        elif overall_score >= 40:
            state = AccountHealthState.AT_RISK
        else:
            state = AccountHealthState.CRITICAL

        # Check expansion readiness
        expansion_signals = self.db.execute(
            select(func.count(ExpansionReadinessSignal.id)).where(
                ExpansionReadinessSignal.tenant_id == tenant_id,
                ExpansionReadinessSignal.is_active.is_(True),
            )
        ).scalar_one()
        if overall_score >= 80 and expansion_signals > 0:
            state = AccountHealthState.EXPANSION_READY

        factor_breakdown = {
            "login_score": login_score,
            "adoption_score": adoption_score,
            "support_score": support_score,
            "training_score": training_score,
            "stability_score": stability_score,
            "open_tickets": open_ticket_count,
            "total_training": total_assignments,
            "completed_training": completed_assignments,
            "expansion_signals": expansion_signals,
        }

        # Get previous snapshot
        prev_stmt = (
            select(AccountHealthSnapshot)
            .where(AccountHealthSnapshot.tenant_id == tenant_id)
            .order_by(AccountHealthSnapshot.snapshot_at.desc())
            .limit(1)
        )
        prev = self.db.execute(prev_stmt).scalar_one_or_none()
        prev_state = prev.overall_state if prev else None
        prev_score = prev.overall_score if prev else None

        explanation_parts = []
        if login_score < 50:
            explanation_parts.append("Low login activity detected.")
        if adoption_score < 50:
            explanation_parts.append("Module adoption is below target.")
        if support_score < 50:
            explanation_parts.append(f"High open support ticket count ({open_ticket_count}).")
        if training_score < 50:
            explanation_parts.append("Training completion is lagging.")
        if stability_score < 50:
            explanation_parts.append("Implementation is stalled or at risk.")
        explanation = " ".join(explanation_parts) if explanation_parts else "Account is healthy across all dimensions."

        snapshot = AccountHealthSnapshot(
            tenant_id=tenant_id,
            overall_state=state,
            overall_score=round(overall_score, 1),
            login_score=round(login_score, 1),
            adoption_score=round(adoption_score, 1),
            support_score=round(support_score, 1),
            training_score=round(training_score, 1),
            stability_score=round(stability_score, 1),
            factor_breakdown=factor_breakdown,
            computation_log={"trigger": trigger, "weights": "15/25/20/20/20", "explanation": explanation},
        )
        self.db.add(snapshot)
        self.db.flush()

        # Health computation log (hardening)
        comp_log = HealthComputationLog(
            tenant_id=tenant_id,
            snapshot_id=snapshot.id,
            trigger=trigger,
            previous_state=prev_state,
            new_state=state,
            previous_score=prev_score,
            new_score=round(overall_score, 1),
            computation_detail=factor_breakdown,
        )
        self.db.add(comp_log)

        # Generate risk factors
        risk_factors = []
        if login_score < 50:
            risk_factors.append(("Low Login Activity", "LOGIN", login_score))
        if adoption_score < 50:
            risk_factors.append(("Low Module Adoption", "ADOPTION", adoption_score))
        if support_score < 50:
            risk_factors.append(("High Support Burden", "SUPPORT", support_score))
        if training_score < 50:
            risk_factors.append(("Training Gaps", "TRAINING", training_score))
        if stability_score < 50:
            risk_factors.append(("Implementation Risk", "STABILITY", stability_score))

        for name, category, score in risk_factors:
            severity = "CRITICAL" if score < 25 else ("HIGH" if score < 40 else "MEDIUM")
            rf = SuccessRiskFactor(
                tenant_id=tenant_id,
                health_snapshot_id=snapshot.id,
                factor_name=name,
                factor_category=category,
                severity=severity,
                impact_score=round(100 - score, 1),
                description=f"{name}: score is {score:.1f}/100",
                recommended_action=f"Investigate {category.lower()} metrics for this tenant.",
                source="HEALTH_COMPUTATION",
            )
            self.db.add(rf)

        self.db.flush()
        return snapshot

    def get_latest_health_snapshot(
        self, tenant_id: uuid.UUID
    ) -> AccountHealthSnapshot | None:
        stmt = (
            select(AccountHealthSnapshot)
            .where(AccountHealthSnapshot.tenant_id == tenant_id)
            .order_by(AccountHealthSnapshot.snapshot_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_adoption_metrics(
        self, tenant_id: uuid.UUID, module_name: str | None = None
    ) -> list[AdoptionMetric]:
        stmt = select(AdoptionMetric).where(
            AdoptionMetric.tenant_id == tenant_id
        ).order_by(AdoptionMetric.measured_at.desc())
        if module_name:
            stmt = stmt.where(AdoptionMetric.module_name == module_name)
        return list(self.db.execute(stmt).scalars().all())

    def list_workflow_adoption_metrics(
        self, tenant_id: uuid.UUID
    ) -> list[WorkflowAdoptionMetric]:
        stmt = (
            select(WorkflowAdoptionMetric)
            .where(WorkflowAdoptionMetric.tenant_id == tenant_id)
            .order_by(WorkflowAdoptionMetric.measured_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    # ══════════════════════════════════════════════════════════════════════════
    # PART 7: RENEWAL & EXPANSION
    # ══════════════════════════════════════════════════════════════════════════

    def list_renewal_risk_signals(
        self, tenant_id: uuid.UUID, active_only: bool = True
    ) -> list[RenewalRiskSignal]:
        stmt = select(RenewalRiskSignal).where(
            RenewalRiskSignal.tenant_id == tenant_id
        ).order_by(RenewalRiskSignal.detected_at.desc())
        if active_only:
            stmt = stmt.where(RenewalRiskSignal.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def create_expansion_opportunity(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        module_name: str,
        opportunity_type: str,
        recommended_action: str,
        evidence: dict | None = None,
        estimated_value_cents: int | None = None,
    ) -> ExpansionOpportunity:
        opp = ExpansionOpportunity(
            tenant_id=tenant_id,
            module_name=module_name,
            opportunity_type=opportunity_type,
            recommended_action=recommended_action,
            evidence=evidence or {},
            estimated_value_cents=estimated_value_cents,
        )
        self.db.add(opp)
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "ExpansionOpportunity", opp.id,
            "CREATED", {"module": module_name, "type": opportunity_type},
        )
        return opp

    def list_expansion_opportunities(
        self, tenant_id: uuid.UUID, state: str | None = None
    ) -> list[ExpansionOpportunity]:
        stmt = select(ExpansionOpportunity).where(
            ExpansionOpportunity.tenant_id == tenant_id
        ).order_by(ExpansionOpportunity.created_at.desc())
        if state:
            stmt = stmt.where(ExpansionOpportunity.state == state)
        return list(self.db.execute(stmt).scalars().all())

    def add_stakeholder_note(
        self,
        tenant_id: uuid.UUID,
        author_user_id: uuid.UUID,
        stakeholder_name: str,
        stakeholder_role: str,
        engagement_type: str,
        content: str,
        sentiment: str | None = None,
    ) -> StakeholderEngagementNote:
        note = StakeholderEngagementNote(
            tenant_id=tenant_id,
            stakeholder_name=stakeholder_name,
            stakeholder_role=stakeholder_role,
            engagement_type=engagement_type,
            content=content,
            sentiment=sentiment,
            author_user_id=author_user_id,
        )
        self.db.add(note)
        self.db.flush()
        return note

    def list_stakeholder_notes(
        self, tenant_id: uuid.UUID
    ) -> list[StakeholderEngagementNote]:
        stmt = select(StakeholderEngagementNote).where(
            StakeholderEngagementNote.tenant_id == tenant_id
        ).order_by(StakeholderEngagementNote.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def create_value_milestone(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        milestone_name: str,
        category: str,
        description: str,
        evidence: dict | None = None,
        impact_summary: str | None = None,
    ) -> ValueMilestone:
        vm = ValueMilestone(
            tenant_id=tenant_id,
            milestone_name=milestone_name,
            category=category,
            description=description,
            evidence=evidence or {},
            impact_summary=impact_summary,
        )
        self.db.add(vm)
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "ValueMilestone", vm.id,
            "CREATED", {"name": milestone_name, "category": category},
        )
        return vm

    def achieve_value_milestone(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        milestone_id: uuid.UUID,
        evidence: dict | None = None,
        impact_summary: str | None = None,
    ) -> ValueMilestone:
        stmt = select(ValueMilestone).where(
            ValueMilestone.tenant_id == tenant_id,
            ValueMilestone.id == milestone_id,
        )
        vm = self.db.execute(stmt).scalar_one_or_none()
        if vm is None:
            raise AppError(code="NOT_FOUND", message="Value milestone not found", status_code=404)
        vm.is_achieved = True
        vm.achieved_at = datetime.now(UTC)
        if evidence:
            vm.evidence = evidence
        if impact_summary:
            vm.impact_summary = impact_summary
        self.db.flush()
        self._audit(
            tenant_id, actor_user_id, "ValueMilestone", vm.id,
            "ACHIEVED", {"name": vm.milestone_name},
        )
        return vm

    def list_value_milestones(
        self, tenant_id: uuid.UUID
    ) -> list[ValueMilestone]:
        stmt = select(ValueMilestone).where(
            ValueMilestone.tenant_id == tenant_id
        ).order_by(ValueMilestone.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    # ══════════════════════════════════════════════════════════════════════════
    # PART 8: FOUNDER SUCCESS COMMAND CENTER
    # ══════════════════════════════════════════════════════════════════════════

    def get_stalled_implementations(self) -> list[CSImplementationProject]:
        stmt = select(CSImplementationProject).where(
            CSImplementationProject.state.in_([
                ImplementationState.STALLED, ImplementationState.ESCALATED,
            ])
        ).order_by(CSImplementationProject.updated_at)
        return list(self.db.execute(stmt).scalars().all())

    def get_high_severity_tickets(self) -> list[SupportTicket]:
        stmt = select(SupportTicket).where(
            SupportTicket.severity.in_([
                SupportSeverityLevel.CRITICAL, SupportSeverityLevel.HIGH,
            ]),
            SupportTicket.status.notin_([
                SupportTicketState.RESOLVED, SupportTicketState.CLOSED,
            ]),
        ).order_by(SupportTicket.created_at)
        return list(self.db.execute(stmt).scalars().all())

    def get_at_risk_accounts(self) -> list[AccountHealthSnapshot]:
        # Latest per tenant
        subq = (
            select(
                AccountHealthSnapshot.tenant_id,
                func.max(AccountHealthSnapshot.snapshot_at).label("latest"),
            )
            .group_by(AccountHealthSnapshot.tenant_id)
            .subquery()
        )
        stmt = (
            select(AccountHealthSnapshot)
            .join(
                subq,
                (AccountHealthSnapshot.tenant_id == subq.c.tenant_id)
                & (AccountHealthSnapshot.snapshot_at == subq.c.latest),
            )
            .where(
                AccountHealthSnapshot.overall_state.in_([
                    AccountHealthState.AT_RISK, AccountHealthState.CRITICAL,
                ])
            )
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_training_gaps(self) -> list[TrainingAssignment]:
        stmt = select(TrainingAssignment).where(
            TrainingAssignment.status.in_([
                TrainingState.OVERDUE, TrainingState.NOT_STARTED,
            ]),
            TrainingAssignment.due_date < datetime.now(UTC),
        ).order_by(TrainingAssignment.due_date)
        return list(self.db.execute(stmt).scalars().all())

    def get_low_adoption_modules(self, threshold: float = 30.0) -> list[AdoptionMetric]:
        week_ago = datetime.now(UTC) - timedelta(days=7)
        stmt = select(AdoptionMetric).where(
            AdoptionMetric.metric_value < threshold,
            AdoptionMetric.measured_at >= week_ago,
        ).order_by(AdoptionMetric.metric_value)
        return list(self.db.execute(stmt).scalars().all())

    def get_expansion_ready_signals(self) -> list[ExpansionReadinessSignal]:
        stmt = select(ExpansionReadinessSignal).where(
            ExpansionReadinessSignal.is_active.is_(True),
        ).order_by(ExpansionReadinessSignal.signal_strength.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_implementation_health_score(self) -> dict:
        projects = list(
            self.db.execute(select(CSImplementationProject)).scalars().all()
        )
        total = len(projects)
        on_track = sum(
            1 for p in projects
            if p.state not in (ImplementationState.STALLED, ImplementationState.ESCALATED, ImplementationState.HANDOFF_COMPLETE)
        )
        at_risk = sum(
            1 for p in projects
            if p.state in (ImplementationState.STALLED, ImplementationState.ESCALATED)
        )
        # Compute average milestone completion across all projects
        all_milestones = list(
            self.db.execute(select(ImplementationMilestone)).scalars().all()
        )
        completed_milestones = sum(
            1 for m in all_milestones if m.status == MilestoneStatus.COMPLETED
        )
        avg_milestone_pct = (
            completed_milestones / max(len(all_milestones), 1)
        ) * 100
        return {
            "total_projects": total,
            "on_track_pct": round(on_track / max(total, 1) * 100, 1),
            "at_risk_pct": round(at_risk / max(total, 1) * 100, 1),
            "avg_milestone_completion_pct": round(avg_milestone_pct, 1),
        }

    def get_support_queue_health(self) -> dict:
        open_states = [
            SupportTicketState.NEW, SupportTicketState.TRIAGED,
            SupportTicketState.ASSIGNED, SupportTicketState.IN_PROGRESS,
            SupportTicketState.WAITING_ON_CUSTOMER, SupportTicketState.WAITING_ON_INTERNAL,
            SupportTicketState.ESCALATED, SupportTicketState.REOPENED,
        ]
        total_open = self.db.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.status.in_(open_states)
            )
        ).scalar_one()
        critical = self.db.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.status.in_(open_states),
                SupportTicket.severity == SupportSeverityLevel.CRITICAL,
            )
        ).scalar_one()
        high = self.db.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.status.in_(open_states),
                SupportTicket.severity == SupportSeverityLevel.HIGH,
            )
        ).scalar_one()
        breached = self.db.execute(
            select(func.count(SupportSLAEvent.id)).where(
                SupportSLAEvent.is_breached.is_(True),
            )
        ).scalar_one()
        # Compute average age in hours for open tickets
        now_utc = datetime.now(UTC)
        open_tickets = list(
            self.db.execute(
                select(SupportTicket).where(
                    SupportTicket.status.in_(open_states)
                )
            ).scalars().all()
        )
        if open_tickets:
            total_hours = sum(
                (now_utc - t.created_at.replace(tzinfo=UTC)).total_seconds() / 3600
                for t in open_tickets
            )
            avg_age = total_hours / len(open_tickets)
        else:
            avg_age = 0.0
        return {
            "total_open": total_open,
            "critical_count": critical,
            "high_count": high,
            "avg_age_hours": round(avg_age, 1),
            "sla_breach_count": breached,
        }

    def get_training_completion_summary(self) -> dict:
        total = self.db.execute(
            select(func.count(TrainingAssignment.id))
        ).scalar_one()
        completed = self.db.execute(
            select(func.count(TrainingAssignment.id)).where(
                TrainingAssignment.status.in_([
                    TrainingState.COMPLETED, TrainingState.VERIFIED,
                ])
            )
        ).scalar_one()
        verified = self.db.execute(
            select(func.count(TrainingAssignment.id)).where(
                TrainingAssignment.status == TrainingState.VERIFIED,
            )
        ).scalar_one()
        overdue = self.db.execute(
            select(func.count(TrainingAssignment.id)).where(
                TrainingAssignment.status == TrainingState.OVERDUE,
            )
        ).scalar_one()
        completed_pct = (completed / max(total, 1)) * 100
        return {
            "total_assignments": total,
            "completed_pct": round(completed_pct, 1),
            "overdue_count": overdue,
            "verified_count": verified,
        }
