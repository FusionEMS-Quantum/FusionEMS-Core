"""
Platform Core Service — Tenant Lifecycle, User Provisioning, Implementation,
Feature Flags, Release/Environment, System Configuration, Founder Command Center.

All mutations are auditable, tenant-scoped, and follow the FusionEMS-Core
service-layer pattern (sync SQLAlchemy session, explicit error taxonomy).
"""
# pylint: disable=not-callable
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.platform_core import (
    AgencyContractLink,
    AgencyImplementationOwner,
    AgencyLifecycleEvent,
    AgencyStatusAudit,
    ConfigDriftAlert,
    ConfigurationChangeAudit,
    ConfigurationValidationIssue,
    ConfigurationVersion,
    DeploymentRecord,
    DeploymentValidation,
    Environment,
    FeatureFlag,
    FeatureFlagAuditEvent,
    FeatureFlagState,
    GoLiveApproval,
    ImplementationAuditEvent,
    ImplementationBlocker,
    ImplementationChecklistItem,
    ImplementationState,
    LaunchReadinessReview,
    ModuleEntitlement,
    ReleaseAuditEvent,
    ReleaseVersion,
    RollbackRecord,
    SystemConfiguration,
    TenantConfiguration,
    TenantFeatureState,
    TenantLifecycleState,
    UserAccessAuditEvent,
    UserModuleVisibility,
    UserOrgMembership,
    UserProvisioningEvent,
    UserRoleAssignment,
)
from core_app.models.platform_core import (
    ImplementationProject as PlatformImplementationProject,
)
from core_app.models.tenant import Tenant
from core_app.models.user import User

# ── Valid lifecycle transitions (A → {B, C, …}) ──────────────────────────────
_LIFECYCLE_TRANSITIONS: dict[str, set[str]] = {
    TenantLifecycleState.TENANT_CREATED: {
        TenantLifecycleState.CONFIG_PENDING,
    },
    TenantLifecycleState.CONFIG_PENDING: {
        TenantLifecycleState.IMPLEMENTATION_IN_PROGRESS,
    },
    TenantLifecycleState.IMPLEMENTATION_IN_PROGRESS: {
        TenantLifecycleState.READY_FOR_GO_LIVE_REVIEW,
        TenantLifecycleState.CONFIG_PENDING,
    },
    TenantLifecycleState.READY_FOR_GO_LIVE_REVIEW: {
        TenantLifecycleState.LIVE,
        TenantLifecycleState.IMPLEMENTATION_IN_PROGRESS,
    },
    TenantLifecycleState.LIVE: {
        TenantLifecycleState.SUSPENDED,
        TenantLifecycleState.ARCHIVED,
    },
    TenantLifecycleState.SUSPENDED: {
        TenantLifecycleState.LIVE,
        TenantLifecycleState.ARCHIVED,
    },
    TenantLifecycleState.ARCHIVED: set(),
}

_IMPLEMENTATION_TRANSITIONS: dict[str, set[str]] = {
    ImplementationState.IMPLEMENTATION_CREATED: {
        ImplementationState.REQUIREMENTS_PENDING,
    },
    ImplementationState.REQUIREMENTS_PENDING: {
        ImplementationState.CONFIG_IN_PROGRESS,
        ImplementationState.BLOCKED,
    },
    ImplementationState.CONFIG_IN_PROGRESS: {
        ImplementationState.READY_FOR_REVIEW,
        ImplementationState.BLOCKED,
    },
    ImplementationState.BLOCKED: {
        ImplementationState.REQUIREMENTS_PENDING,
        ImplementationState.CONFIG_IN_PROGRESS,
        ImplementationState.READY_FOR_REVIEW,
    },
    ImplementationState.READY_FOR_REVIEW: {
        ImplementationState.GO_LIVE_APPROVED,
        ImplementationState.CONFIG_IN_PROGRESS,
        ImplementationState.BLOCKED,
    },
    ImplementationState.GO_LIVE_APPROVED: {
        ImplementationState.GO_LIVE_SCHEDULED,
        ImplementationState.BLOCKED,
    },
    ImplementationState.GO_LIVE_SCHEDULED: {
        ImplementationState.LIVE_STABILIZATION,
        ImplementationState.BLOCKED,
    },
    ImplementationState.LIVE_STABILIZATION: {
        ImplementationState.IMPLEMENTATION_COMPLETE,
        ImplementationState.BLOCKED,
    },
    ImplementationState.IMPLEMENTATION_COMPLETE: set(),
}


class PlatformCoreService:
    """Unified service for all platform-core domain operations (Parts 1–7)."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL AUDIT HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _agency_audit(
        self,
        tenant_id: uuid.UUID,
        field_name: str,
        old_value: str | None,
        new_value: str,
        actor_user_id: uuid.UUID | None,
        reason: str,
        correlation_id: str | None = None,
    ) -> AgencyStatusAudit:
        evt = AgencyStatusAudit(
            tenant_id=tenant_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            actor_user_id=actor_user_id,
            reason=reason,
            correlation_id=correlation_id,
        )
        self.db.add(evt)
        return evt

    def _user_access_audit(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        action: str,
        actor_user_id: uuid.UUID | None,
        old_value: str | None = None,
        new_value: str | None = None,
        reason: str | None = None,
        correlation_id: str | None = None,
    ) -> UserAccessAuditEvent:
        evt = UserAccessAuditEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            actor_user_id=actor_user_id,
            reason=reason,
            correlation_id=correlation_id,
        )
        self.db.add(evt)
        return evt

    def _impl_audit(
        self,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID,
        action: str,
        detail: str,
        actor_user_id: uuid.UUID | None,
        correlation_id: str | None = None,
    ) -> ImplementationAuditEvent:
        evt = ImplementationAuditEvent(
            project_id=project_id,
            tenant_id=tenant_id,
            action=action,
            detail=detail,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        )
        self.db.add(evt)
        return evt

    def _ff_audit(
        self,
        feature_flag_id: uuid.UUID,
        action: str,
        actor_user_id: uuid.UUID | None,
        tenant_id: uuid.UUID | None = None,
        old_state: str | None = None,
        new_state: str | None = None,
        reason: str | None = None,
        correlation_id: str | None = None,
    ) -> FeatureFlagAuditEvent:
        evt = FeatureFlagAuditEvent(
            feature_flag_id=feature_flag_id,
            tenant_id=tenant_id,
            action=action,
            old_state=old_state,
            new_state=new_state,
            actor_user_id=actor_user_id,
            reason=reason,
            correlation_id=correlation_id,
        )
        self.db.add(evt)
        return evt

    def _release_audit(
        self,
        action: str,
        actor: str,
        detail: str,
        environment_id: uuid.UUID | None = None,
        release_version_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
    ) -> ReleaseAuditEvent:
        evt = ReleaseAuditEvent(
            environment_id=environment_id,
            release_version_id=release_version_id,
            action=action,
            actor=actor,
            detail=detail,
            correlation_id=correlation_id,
        )
        self.db.add(evt)
        return evt

    def _config_change_audit(
        self,
        config_table: str,
        config_key: str,
        action: str,
        new_value: dict[str, Any],
        actor_user_id: uuid.UUID | None,
        tenant_id: uuid.UUID | None = None,
        old_value: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> ConfigurationChangeAudit:
        evt = ConfigurationChangeAudit(
            config_table=config_table,
            config_key=config_key,
            tenant_id=tenant_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        )
        self.db.add(evt)
        return evt

    # ══════════════════════════════════════════════════════════════════════════
    # PART 1: TENANT / AGENCY LIFECYCLE
    # ══════════════════════════════════════════════════════════════════════════

    def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = self.db.get(Tenant, tenant_id)
        if tenant is None:
            raise AppError(code="NOT_FOUND", message="Tenant not found", status_code=404)
        return tenant

    def transition_tenant_lifecycle(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        to_state: str,
        reason: str,
        correlation_id: str | None = None,
    ) -> Tenant:
        tenant = self.get_tenant(tenant_id)
        from_state = tenant.lifecycle_state

        try:
            TenantLifecycleState(to_state)
        except ValueError as exc:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Invalid lifecycle state: {to_state}",
                status_code=400,
            ) from exc

        valid_targets = _LIFECYCLE_TRANSITIONS.get(from_state, set())
        if to_state not in valid_targets:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Cannot transition from {from_state} to {to_state}",
                status_code=409,
            )

        tenant.lifecycle_state = to_state

        lifecycle_event = AgencyLifecycleEvent(
            tenant_id=tenant_id,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        )
        self.db.add(lifecycle_event)

        self._agency_audit(
            tenant_id=tenant_id,
            field_name="lifecycle_state",
            old_value=from_state,
            new_value=to_state,
            actor_user_id=actor_user_id,
            reason=reason,
            correlation_id=correlation_id,
        )
        self.db.flush()
        return tenant

    def list_lifecycle_events(
        self, tenant_id: uuid.UUID, limit: int = 100
    ) -> list[AgencyLifecycleEvent]:
        stmt = (
            select(AgencyLifecycleEvent)
            .where(AgencyLifecycleEvent.tenant_id == tenant_id)
            .order_by(AgencyLifecycleEvent.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def assign_implementation_owner(
        self,
        tenant_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        assigned_by_user_id: uuid.UUID | None,
        role_label: str = "implementation_lead",
    ) -> AgencyImplementationOwner:
        rec = AgencyImplementationOwner(
            tenant_id=tenant_id,
            owner_user_id=owner_user_id,
            role_label=role_label,
            assigned_by_user_id=assigned_by_user_id,
        )
        self.db.add(rec)
        self.db.flush()
        self._agency_audit(
            tenant_id=tenant_id,
            field_name="implementation_owner",
            old_value=None,
            new_value=str(owner_user_id),
            actor_user_id=assigned_by_user_id,
            reason=f"Assigned {role_label}",
        )
        return rec

    def create_contract_link(
        self,
        tenant_id: uuid.UUID,
        contract_type: str,
        external_contract_id: str | None = None,
        signed_at: datetime | None = None,
        expires_at: datetime | None = None,
        metadata_blob: dict[str, Any] | None = None,
    ) -> AgencyContractLink:
        rec = AgencyContractLink(
            tenant_id=tenant_id,
            contract_type=contract_type,
            external_contract_id=external_contract_id,
            signed_at=signed_at,
            expires_at=expires_at,
            metadata_blob=metadata_blob or {},
        )
        self.db.add(rec)
        self.db.flush()
        return rec

    def list_contract_links(
        self, tenant_id: uuid.UUID
    ) -> list[AgencyContractLink]:
        stmt = (
            select(AgencyContractLink)
            .where(AgencyContractLink.tenant_id == tenant_id)
            .order_by(AgencyContractLink.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    # ══════════════════════════════════════════════════════════════════════════
    # PART 2: USER / ACCESS PROVISIONING
    # ══════════════════════════════════════════════════════════════════════════

    def invite_user(
        self,
        tenant_id: uuid.UUID,
        email: str,
        role: str,
        actor_user_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> User:
        from core_app.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.db)
        existing = user_repo.get_by_email_and_tenant(email.lower(), tenant_id)
        if existing is not None:
            raise AppError(
                code="CONFLICT", message="User already exists for this tenant", status_code=409
            )
        user = user_repo.create(
            tenant_id=tenant_id, email=email.lower(), hashed_password="INVITED", role=role
        )
        user.status = "invited"
        self.db.flush()

        # Org membership
        membership = UserOrgMembership(
            user_id=user.id, tenant_id=tenant_id, status="active"
        )
        self.db.add(membership)

        # Provisioning event
        prov_event = UserProvisioningEvent(
            tenant_id=tenant_id,
            user_id=user.id,
            event_type="INVITED",
            detail=f"User {email} invited with role {role}",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        )
        self.db.add(prov_event)

        self._user_access_audit(
            tenant_id=tenant_id,
            user_id=user.id,
            action="INVITE",
            actor_user_id=actor_user_id,
            new_value=role,
            reason=f"User {email} invited",
            correlation_id=correlation_id,
        )
        self.db.flush()
        return user

    def activate_user(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> User:
        from core_app.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.db)
        user = user_repo.get_by_id_and_tenant(user_id, tenant_id)
        if user is None:
            raise AppError(code="NOT_FOUND", message="User not found", status_code=404)
        old_status = user.status
        user.status = "active"
        self.db.flush()

        prov_event = UserProvisioningEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="ACTIVATED",
            detail=f"User activated from {old_status}",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        )
        self.db.add(prov_event)
        self._user_access_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="ACTIVATE",
            actor_user_id=actor_user_id,
            old_value=old_status,
            new_value="active",
            correlation_id=correlation_id,
        )
        self.db.flush()
        return user

    def disable_user(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
        correlation_id: str | None = None,
    ) -> User:
        from core_app.repositories.user_repository import UserRepository

        user_repo = UserRepository(self.db)
        user = user_repo.get_by_id_and_tenant(user_id, tenant_id)
        if user is None:
            raise AppError(code="NOT_FOUND", message="User not found", status_code=404)
        old_status = user.status
        user.status = "disabled"
        self.db.flush()

        prov_event = UserProvisioningEvent(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type="DISABLED",
            detail=f"User disabled: {reason}",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        )
        self.db.add(prov_event)
        self._user_access_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="DISABLE",
            actor_user_id=actor_user_id,
            old_value=old_status,
            new_value="disabled",
            reason=reason,
            correlation_id=correlation_id,
        )
        self.db.flush()
        return user

    def assign_role(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role_name: str,
        actor_user_id: uuid.UUID,
        reason: str,
        correlation_id: str | None = None,
    ) -> UserRoleAssignment:
        assignment = UserRoleAssignment(
            user_id=user_id,
            tenant_id=tenant_id,
            role_name=role_name,
            assigned_by_user_id=actor_user_id,
            reason=reason,
        )
        self.db.add(assignment)
        self.db.flush()
        self._user_access_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="ROLE_ASSIGNED",
            actor_user_id=actor_user_id,
            new_value=role_name,
            reason=reason,
            correlation_id=correlation_id,
        )
        return assignment

    def revoke_role(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role_name: str,
        actor_user_id: uuid.UUID,
        reason: str,
        correlation_id: str | None = None,
    ) -> UserRoleAssignment:
        stmt = select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id,
            UserRoleAssignment.tenant_id == tenant_id,
            UserRoleAssignment.role_name == role_name,
            UserRoleAssignment.is_active.is_(True),
        )
        assignment = self.db.execute(stmt).scalar_one_or_none()
        if assignment is None:
            raise AppError(
                code="NOT_FOUND",
                message=f"Active role assignment '{role_name}' not found for user",
                status_code=404,
            )
        assignment.is_active = False
        assignment.revoked_at = datetime.now(UTC)
        assignment.revoked_by_user_id = actor_user_id
        self.db.flush()
        self._user_access_audit(
            tenant_id=tenant_id,
            user_id=user_id,
            action="ROLE_REVOKED",
            actor_user_id=actor_user_id,
            old_value=role_name,
            reason=reason,
            correlation_id=correlation_id,
        )
        return assignment

    def list_user_roles(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[UserRoleAssignment]:
        stmt = (
            select(UserRoleAssignment)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.tenant_id == tenant_id,
            )
            .order_by(UserRoleAssignment.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_provisioning_events(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None, limit: int = 100
    ) -> list[UserProvisioningEvent]:
        stmt = (
            select(UserProvisioningEvent)
            .where(UserProvisioningEvent.tenant_id == tenant_id)
            .order_by(UserProvisioningEvent.created_at.desc())
            .limit(limit)
        )
        if user_id:
            stmt = stmt.where(UserProvisioningEvent.user_id == user_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_user_module_visibility(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[UserModuleVisibility]:
        stmt = select(UserModuleVisibility).where(
            UserModuleVisibility.user_id == user_id,
            UserModuleVisibility.tenant_id == tenant_id,
        )
        return list(self.db.execute(stmt).scalars().all())

    # ══════════════════════════════════════════════════════════════════════════
    # PART 3: IMPLEMENTATION / ONBOARDING
    # ══════════════════════════════════════════════════════════════════════════

    def create_implementation_project(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        target_go_live_date: datetime | None = None,
        notes: str | None = None,
    ) -> PlatformImplementationProject:
        project = PlatformImplementationProject(
            tenant_id=tenant_id,
            owner_user_id=actor_user_id,
            target_go_live_date=target_go_live_date,
            notes=notes,
        )
        self.db.add(project)
        self.db.flush()
        self._impl_audit(
            project.id, tenant_id, "CREATED",
            "Implementation project created", actor_user_id,
        )
        return project

    def get_implementation_project(
        self, tenant_id: uuid.UUID, project_id: uuid.UUID
    ) -> PlatformImplementationProject:
        stmt = select(PlatformImplementationProject).where(
            PlatformImplementationProject.tenant_id == tenant_id,
            PlatformImplementationProject.id == project_id,
        )
        project = self.db.execute(stmt).scalar_one_or_none()
        if project is None:
            raise AppError(code="NOT_FOUND", message="Implementation project not found", status_code=404)
        return project

    def list_implementation_projects(
        self, tenant_id: uuid.UUID, state: str | None = None
    ) -> list[PlatformImplementationProject]:
        stmt = (
            select(PlatformImplementationProject)
            .where(PlatformImplementationProject.tenant_id == tenant_id)
            .order_by(PlatformImplementationProject.created_at.desc())
        )
        if state:
            stmt = stmt.where(PlatformImplementationProject.current_state == state)
        return list(self.db.execute(stmt).scalars().all())

    def transition_implementation_state(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        to_state: str,
        reason: str,
        correlation_id: str | None = None,
    ) -> PlatformImplementationProject:
        project = self.get_implementation_project(tenant_id, project_id)
        from_state = project.current_state

        try:
            ImplementationState(to_state)
        except ValueError as exc:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Invalid implementation state: {to_state}",
                status_code=400,
            ) from exc

        valid_targets = _IMPLEMENTATION_TRANSITIONS.get(from_state, set())
        if to_state not in valid_targets:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Cannot transition from {from_state} to {to_state}",
                status_code=409,
            )

        project.current_state = to_state
        project.version += 1
        if to_state == ImplementationState.IMPLEMENTATION_COMPLETE:
            project.actual_go_live_date = datetime.now(UTC)
        self.db.flush()

        self._impl_audit(
            project.id, tenant_id,
            "STATE_CHANGED",
            f"Transitioned from {from_state} to {to_state}: {reason}",
            actor_user_id, correlation_id,
        )
        return project

    def add_checklist_item(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        category: str,
        title: str,
        description: str | None = None,
        is_required: bool = True,
        owner_user_id: uuid.UUID | None = None,
        sort_order: int = 0,
    ) -> ImplementationChecklistItem:
        project = self.get_implementation_project(tenant_id, project_id)
        item = ImplementationChecklistItem(
            project_id=project.id,
            category=category,
            title=title,
            description=description,
            is_required=is_required,
            owner_user_id=owner_user_id,
            sort_order=sort_order,
        )
        self.db.add(item)
        self.db.flush()
        self._impl_audit(
            project.id, tenant_id,
            "CHECKLIST_ITEM_ADDED",
            f"Added checklist item: {title}",
            actor_user_id,
        )
        return item

    def update_checklist_item(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        status: str | None = None,
        owner_user_id: uuid.UUID | None = None,
    ) -> ImplementationChecklistItem:
        project = self.get_implementation_project(tenant_id, project_id)
        stmt = select(ImplementationChecklistItem).where(
            ImplementationChecklistItem.id == item_id,
            ImplementationChecklistItem.project_id == project.id,
        )
        item = self.db.execute(stmt).scalar_one_or_none()
        if item is None:
            raise AppError(code="NOT_FOUND", message="Checklist item not found", status_code=404)
        if status is not None:
            old_status = item.status
            item.status = status
            if status == "completed":
                item.completed_at = datetime.now(UTC)
                item.completed_by_user_id = actor_user_id
            self._impl_audit(
                project.id, tenant_id,
                "CHECKLIST_ITEM_UPDATED",
                f"Item '{item.title}' status: {old_status} → {status}",
                actor_user_id,
            )
        if owner_user_id is not None:
            item.owner_user_id = owner_user_id
        self.db.flush()
        return item

    def list_checklist_items(
        self, tenant_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[ImplementationChecklistItem]:
        project = self.get_implementation_project(tenant_id, project_id)
        stmt = (
            select(ImplementationChecklistItem)
            .where(ImplementationChecklistItem.project_id == project.id)
            .order_by(ImplementationChecklistItem.sort_order)
        )
        return list(self.db.execute(stmt).scalars().all())

    def add_blocker(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        title: str,
        description: str,
        severity: str = "HIGH",
        owner_user_id: uuid.UUID | None = None,
    ) -> ImplementationBlocker:
        project = self.get_implementation_project(tenant_id, project_id)
        blocker = ImplementationBlocker(
            project_id=project.id,
            title=title,
            description=description,
            severity=severity,
            owner_user_id=owner_user_id,
        )
        self.db.add(blocker)
        self.db.flush()
        self._impl_audit(
            project.id, tenant_id,
            "BLOCKER_ADDED",
            f"Blocker added: {title} [{severity}]",
            actor_user_id,
        )
        return blocker

    def resolve_blocker(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        blocker_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        resolution_notes: str,
        reason: str,
    ) -> ImplementationBlocker:
        project = self.get_implementation_project(tenant_id, project_id)
        stmt = select(ImplementationBlocker).where(
            ImplementationBlocker.id == blocker_id,
            ImplementationBlocker.project_id == project.id,
        )
        blocker = self.db.execute(stmt).scalar_one_or_none()
        if blocker is None:
            raise AppError(code="NOT_FOUND", message="Blocker not found", status_code=404)
        blocker.status = "resolved"
        blocker.resolved_at = datetime.now(UTC)
        blocker.resolved_by_user_id = actor_user_id
        blocker.resolution_notes = resolution_notes
        self.db.flush()
        self._impl_audit(
            project.id, tenant_id,
            "BLOCKER_RESOLVED",
            f"Blocker resolved: {blocker.title} — {reason}",
            actor_user_id,
        )
        return blocker

    def list_blockers(
        self, tenant_id: uuid.UUID, project_id: uuid.UUID, status: str | None = None
    ) -> list[ImplementationBlocker]:
        project = self.get_implementation_project(tenant_id, project_id)
        stmt = (
            select(ImplementationBlocker)
            .where(ImplementationBlocker.project_id == project.id)
            .order_by(ImplementationBlocker.created_at.desc())
        )
        if status:
            stmt = stmt.where(ImplementationBlocker.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def request_go_live_approval(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
    ) -> GoLiveApproval:
        project = self.get_implementation_project(tenant_id, project_id)

        # Snapshot current checklist and blockers
        checklist_items = self.list_checklist_items(tenant_id, project_id)
        blockers = self.list_blockers(tenant_id, project_id)

        open_required = [c for c in checklist_items if c.is_required and c.status != "completed"]
        open_blockers = [b for b in blockers if b.status == "open"]

        checklist_snapshot = {
            "total": len(checklist_items),
            "completed": len([c for c in checklist_items if c.status == "completed"]),
            "open_required": len(open_required),
        }
        blocker_snapshot = {
            "total": len(blockers),
            "open": len(open_blockers),
            "items": [{"title": b.title, "severity": b.severity} for b in open_blockers],
        }

        approval = GoLiveApproval(
            project_id=project.id,
            tenant_id=tenant_id,
            checklist_snapshot=checklist_snapshot,
            blocker_snapshot=blocker_snapshot,
        )
        self.db.add(approval)
        self.db.flush()

        self._impl_audit(
            project.id, tenant_id,
            "GO_LIVE_REQUESTED",
            f"Go-live approval requested: {reason}",
            actor_user_id,
        )
        return approval

    def approve_go_live(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        approval_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> GoLiveApproval:
        self.get_implementation_project(tenant_id, project_id)
        stmt = select(GoLiveApproval).where(
            GoLiveApproval.id == approval_id,
            GoLiveApproval.project_id == project_id,
            GoLiveApproval.tenant_id == tenant_id,
        )
        approval = self.db.execute(stmt).scalar_one_or_none()
        if approval is None:
            raise AppError(code="NOT_FOUND", message="Go-live approval not found", status_code=404)
        approval.status = "approved"
        approval.approved_by_user_id = actor_user_id
        approval.approved_at = datetime.now(UTC)
        self.db.flush()
        self._impl_audit(
            project_id, tenant_id,
            "GO_LIVE_APPROVED",
            f"Go-live approved by {actor_user_id}",
            actor_user_id,
        )
        return approval

    def create_launch_readiness_review(
        self,
        tenant_id: uuid.UUID,
        project_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        overall_score: int,
        verdict: str,
        config_score: int = 0,
        billing_score: int = 0,
        telecom_score: int = 0,
        compliance_score: int = 0,
        notes: str | None = None,
        findings: dict[str, Any] | None = None,
    ) -> LaunchReadinessReview:
        self.get_implementation_project(tenant_id, project_id)
        review = LaunchReadinessReview(
            project_id=project_id,
            tenant_id=tenant_id,
            reviewer_user_id=reviewer_user_id,
            overall_score=overall_score,
            config_score=config_score,
            billing_score=billing_score,
            telecom_score=telecom_score,
            compliance_score=compliance_score,
            verdict=verdict,
            notes=notes,
            findings=findings or {},
        )
        self.db.add(review)
        self.db.flush()
        self._impl_audit(
            project_id, tenant_id,
            "READINESS_REVIEW_CREATED",
            f"Launch readiness review: score={overall_score}, verdict={verdict}",
            reviewer_user_id,
        )
        return review

    # ══════════════════════════════════════════════════════════════════════════
    # PART 4: FEATURE FLAGS / MODULE ENTITLEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def create_feature_flag(
        self,
        actor_user_id: uuid.UUID,
        flag_key: str,
        display_name: str,
        description: str | None = None,
        default_state: str = "DISABLED",
        category: str = "general",
        is_critical: bool = False,
        requires_billing: bool = False,
        environment_scope: str | None = None,
    ) -> FeatureFlag:
        flag = FeatureFlag(
            flag_key=flag_key,
            display_name=display_name,
            description=description,
            default_state=default_state,
            category=category,
            is_critical=is_critical,
            requires_billing=requires_billing,
            environment_scope=environment_scope,
        )
        self.db.add(flag)
        self.db.flush()
        self._ff_audit(
            flag.id, "CREATED", actor_user_id,
            new_state=default_state, reason=f"Feature flag created: {flag_key}",
        )
        return flag

    def list_feature_flags(self) -> list[FeatureFlag]:
        stmt = select(FeatureFlag).order_by(FeatureFlag.flag_key)
        return list(self.db.execute(stmt).scalars().all())

    def get_feature_flag(self, flag_id: uuid.UUID) -> FeatureFlag:
        flag = self.db.get(FeatureFlag, flag_id)
        if flag is None:
            raise AppError(code="NOT_FOUND", message="Feature flag not found", status_code=404)
        return flag

    def set_tenant_feature_state(
        self,
        tenant_id: uuid.UUID,
        feature_flag_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        state: str,
        reason: str,
        rollout_percentage: int | None = None,
        notes: str | None = None,
        correlation_id: str | None = None,
    ) -> TenantFeatureState:
        try:
            FeatureFlagState(state)
        except ValueError as exc:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Invalid feature flag state: {state}",
                status_code=400,
            ) from exc

        # Verify flag exists
        self.get_feature_flag(feature_flag_id)

        stmt = select(TenantFeatureState).where(
            TenantFeatureState.tenant_id == tenant_id,
            TenantFeatureState.feature_flag_id == feature_flag_id,
        )
        tfs = self.db.execute(stmt).scalar_one_or_none()
        old_state: str | None = None

        if tfs is None:
            tfs = TenantFeatureState(
                tenant_id=tenant_id,
                feature_flag_id=feature_flag_id,
                current_state=state,
                rollout_percentage=rollout_percentage,
                notes=notes,
            )
            self.db.add(tfs)
        else:
            old_state = tfs.current_state
            tfs.current_state = state
            tfs.rollout_percentage = rollout_percentage
            tfs.notes = notes
            tfs.version += 1

        if state in (FeatureFlagState.ENABLED, FeatureFlagState.LIMITED_ROLLOUT, FeatureFlagState.BETA_ENABLED):
            tfs.enabled_at = datetime.now(UTC)
            tfs.enabled_by_user_id = actor_user_id

        self.db.flush()
        self._ff_audit(
            feature_flag_id, "STATE_CHANGED", actor_user_id,
            tenant_id=tenant_id, old_state=old_state, new_state=state,
            reason=reason, correlation_id=correlation_id,
        )
        return tfs

    def list_tenant_feature_states(
        self, tenant_id: uuid.UUID
    ) -> list[TenantFeatureState]:
        stmt = (
            select(TenantFeatureState)
            .where(TenantFeatureState.tenant_id == tenant_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_module_entitlements(
        self, tenant_id: uuid.UUID
    ) -> list[ModuleEntitlement]:
        stmt = (
            select(ModuleEntitlement)
            .where(ModuleEntitlement.tenant_id == tenant_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def entitlement_vs_runtime_report(
        self, tenant_id: uuid.UUID
    ) -> dict[str, Any]:
        entitlements = self.list_module_entitlements(tenant_id)
        feature_states = self.list_tenant_feature_states(tenant_id)

        entitled_modules = {e.module_name for e in entitlements if e.is_entitled}
        enabled_flags = {
            str(f.feature_flag_id) for f in feature_states
            if f.current_state in (
                FeatureFlagState.ENABLED,
                FeatureFlagState.LIMITED_ROLLOUT,
                FeatureFlagState.BETA_ENABLED,
            )
        }

        mismatches: list[dict[str, Any]] = []
        for ent in entitlements:
            # Find matching flag by module name convention
            matching = [
                f for f in feature_states
                if f.current_state in (
                    FeatureFlagState.ENABLED,
                    FeatureFlagState.LIMITED_ROLLOUT,
                    FeatureFlagState.BETA_ENABLED,
                )
            ]
            if ent.is_entitled and not matching:
                mismatches.append({
                    "module": ent.module_name,
                    "entitled": True,
                    "runtime_enabled": False,
                    "issue": "Entitled but not enabled at runtime",
                })

        return {
            "tenant_id": str(tenant_id),
            "mismatches": mismatches,
            "total_entitled": len(entitled_modules),
            "total_runtime_enabled": len(enabled_flags),
            "drift_detected": len(mismatches) > 0,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # PART 5: RELEASE / ENVIRONMENT CONTROL
    # ══════════════════════════════════════════════════════════════════════════

    def list_environments(self) -> list[Environment]:
        stmt = select(Environment).order_by(Environment.name)
        return list(self.db.execute(stmt).scalars().all())

    def get_environment(self, env_id: uuid.UUID) -> Environment:
        env = self.db.get(Environment, env_id)
        if env is None:
            raise AppError(code="NOT_FOUND", message="Environment not found", status_code=404)
        return env

    def create_release_version(
        self,
        actor: str,
        version_tag: str,
        git_sha: str,
        release_notes: str | None = None,
        migration_count: int = 0,
        created_by: str | None = None,
    ) -> ReleaseVersion:
        release = ReleaseVersion(
            version_tag=version_tag,
            git_sha=git_sha,
            release_notes=release_notes,
            migration_count=migration_count,
            created_by=created_by or actor,
        )
        self.db.add(release)
        self.db.flush()
        self._release_audit(
            "RELEASE_CREATED", actor,
            f"Release {version_tag} created (sha={git_sha[:12]})",
            release_version_id=release.id,
        )
        return release

    def list_release_versions(self, limit: int = 50) -> list[ReleaseVersion]:
        stmt = (
            select(ReleaseVersion)
            .order_by(ReleaseVersion.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_deployment_record(
        self,
        actor: str,
        environment_id: uuid.UUID,
        release_version_id: uuid.UUID,
        deployed_by: str,
    ) -> DeploymentRecord:
        self.get_environment(environment_id)
        rec = DeploymentRecord(
            environment_id=environment_id,
            release_version_id=release_version_id,
            deployed_by=deployed_by,
        )
        self.db.add(rec)
        self.db.flush()
        self._release_audit(
            "DEPLOYMENT_STARTED", actor,
            f"Deployment started to env {environment_id}",
            environment_id=environment_id,
            release_version_id=release_version_id,
        )
        return rec

    def complete_deployment(
        self,
        deployment_id: uuid.UUID,
        actor: str,
        outcome: str,
        error_detail: str | None = None,
    ) -> DeploymentRecord:
        dep = self.db.get(DeploymentRecord, deployment_id)
        if dep is None:
            raise AppError(code="NOT_FOUND", message="Deployment record not found", status_code=404)
        dep.current_state = "DEPLOYED" if outcome == "success" else "DEGRADED"
        dep.outcome = outcome
        dep.completed_at = datetime.now(UTC)
        dep.error_detail = error_detail
        self.db.flush()

        # Update environment
        env = self.get_environment(dep.environment_id)
        release = self.db.get(ReleaseVersion, dep.release_version_id)
        if release and outcome == "success":
            env.current_version = release.version_tag
            env.current_git_sha = release.git_sha
            env.deployed_at = dep.completed_at
            env.health_status = "healthy"
        elif outcome != "success":
            env.health_status = "degraded"
        self.db.flush()

        self._release_audit(
            "DEPLOYMENT_COMPLETED", actor,
            f"Deployment {deployment_id} completed: {outcome}",
            environment_id=dep.environment_id,
            release_version_id=dep.release_version_id,
        )
        return dep

    def add_deployment_validation(
        self,
        deployment_id: uuid.UUID,
        validation_type: str,
        status: str,
        details: dict[str, Any] | None = None,
        validated_by: str | None = None,
    ) -> DeploymentValidation:
        dep = self.db.get(DeploymentRecord, deployment_id)
        if dep is None:
            raise AppError(code="NOT_FOUND", message="Deployment record not found", status_code=404)
        val = DeploymentValidation(
            deployment_record_id=deployment_id,
            validation_type=validation_type,
            status=status,
            details=details or {},
            validated_by=validated_by,
        )
        self.db.add(val)
        self.db.flush()
        return val

    def create_rollback(
        self,
        environment_id: uuid.UUID,
        from_version_id: uuid.UUID,
        to_version_id: uuid.UUID,
        reason: str,
        initiated_by: str,
    ) -> RollbackRecord:
        rec = RollbackRecord(
            environment_id=environment_id,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
            reason=reason,
            initiated_by=initiated_by,
        )
        self.db.add(rec)
        self.db.flush()
        self._release_audit(
            "ROLLBACK_INITIATED", initiated_by,
            f"Rollback from {from_version_id} to {to_version_id}: {reason}",
            environment_id=environment_id,
        )
        return rec

    def list_config_drift_alerts(
        self, environment_id: uuid.UUID | None = None, resolved: bool | None = None
    ) -> list[ConfigDriftAlert]:
        stmt = select(ConfigDriftAlert).order_by(ConfigDriftAlert.created_at.desc())
        if environment_id:
            stmt = stmt.where(ConfigDriftAlert.environment_id == environment_id)
        if resolved is not None:
            stmt = stmt.where(ConfigDriftAlert.resolved == resolved)
        return list(self.db.execute(stmt).scalars().all())

    # ══════════════════════════════════════════════════════════════════════════
    # PART 6: SYSTEM CONFIGURATION
    # ══════════════════════════════════════════════════════════════════════════

    def set_tenant_configuration(
        self,
        tenant_id: uuid.UUID,
        config_key: str,
        config_value: dict[str, Any],
        actor_user_id: uuid.UUID,
        category: str = "general",
        is_sensitive: bool = False,
        correlation_id: str | None = None,
    ) -> TenantConfiguration:
        stmt = select(TenantConfiguration).where(
            TenantConfiguration.tenant_id == tenant_id,
            TenantConfiguration.config_key == config_key,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        old_value: dict[str, Any] | None = None

        if existing:
            old_value = existing.config_value
            existing.config_value = config_value
            existing.category = category
            existing.is_sensitive = is_sensitive
            existing.version += 1
            existing.last_validated_at = datetime.now(UTC)
            existing.validation_status = "valid"
            self.db.flush()
            config = existing
        else:
            config = TenantConfiguration(
                tenant_id=tenant_id,
                config_key=config_key,
                config_value=config_value,
                category=category,
                is_sensitive=is_sensitive,
                last_validated_at=datetime.now(UTC),
                validation_status="valid",
            )
            self.db.add(config)
            self.db.flush()

        # Version snapshot
        version_snap = ConfigurationVersion(
            config_table="tenant_configurations",
            config_key=config_key,
            tenant_id=tenant_id,
            version_number=config.version,
            snapshot=config_value,
            changed_by_user_id=actor_user_id,
            change_reason="Updated" if old_value else "Created",
        )
        self.db.add(version_snap)

        self._config_change_audit(
            "tenant_configurations", config_key,
            "UPDATE" if old_value else "CREATE",
            config_value, actor_user_id,
            tenant_id=tenant_id, old_value=old_value,
            correlation_id=correlation_id,
        )
        self.db.flush()
        return config

    def get_tenant_configuration(
        self, tenant_id: uuid.UUID, config_key: str
    ) -> TenantConfiguration:
        stmt = select(TenantConfiguration).where(
            TenantConfiguration.tenant_id == tenant_id,
            TenantConfiguration.config_key == config_key,
        )
        config = self.db.execute(stmt).scalar_one_or_none()
        if config is None:
            raise AppError(code="NOT_FOUND", message=f"Configuration key '{config_key}' not found", status_code=404)
        return config

    def list_tenant_configurations(
        self, tenant_id: uuid.UUID, category: str | None = None
    ) -> list[TenantConfiguration]:
        stmt = (
            select(TenantConfiguration)
            .where(TenantConfiguration.tenant_id == tenant_id)
            .order_by(TenantConfiguration.config_key)
        )
        if category:
            stmt = stmt.where(TenantConfiguration.category == category)
        return list(self.db.execute(stmt).scalars().all())

    def set_system_configuration(
        self,
        config_key: str,
        config_value: dict[str, Any],
        actor_user_id: uuid.UUID,
        category: str = "general",
        is_sensitive: bool = False,
        environment: str | None = None,
        correlation_id: str | None = None,
    ) -> SystemConfiguration:
        stmt = select(SystemConfiguration).where(
            SystemConfiguration.config_key == config_key,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        old_value: dict[str, Any] | None = None

        if existing:
            old_value = existing.config_value
            existing.config_value = config_value
            existing.category = category
            existing.is_sensitive = is_sensitive
            existing.environment = environment
            existing.version += 1
            self.db.flush()
            config = existing
        else:
            config = SystemConfiguration(
                config_key=config_key,
                config_value=config_value,
                category=category,
                is_sensitive=is_sensitive,
                environment=environment,
            )
            self.db.add(config)
            self.db.flush()

        # Version snapshot
        version_snap = ConfigurationVersion(
            config_table="system_configurations",
            config_key=config_key,
            version_number=config.version,
            snapshot=config_value,
            changed_by_user_id=actor_user_id,
            change_reason="Updated" if old_value else "Created",
        )
        self.db.add(version_snap)

        self._config_change_audit(
            "system_configurations", config_key,
            "UPDATE" if old_value else "CREATE",
            config_value, actor_user_id,
            old_value=old_value, correlation_id=correlation_id,
        )
        self.db.flush()
        return config

    def list_system_configurations(
        self, category: str | None = None, environment: str | None = None
    ) -> list[SystemConfiguration]:
        stmt = select(SystemConfiguration).order_by(SystemConfiguration.config_key)
        if category:
            stmt = stmt.where(SystemConfiguration.category == category)
        if environment:
            stmt = stmt.where(SystemConfiguration.environment == environment)
        return list(self.db.execute(stmt).scalars().all())

    def get_config_version_history(
        self, config_key: str, tenant_id: uuid.UUID | None = None, limit: int = 20
    ) -> list[ConfigurationVersion]:
        stmt = (
            select(ConfigurationVersion)
            .where(ConfigurationVersion.config_key == config_key)
            .order_by(ConfigurationVersion.version_number.desc())
            .limit(limit)
        )
        if tenant_id:
            stmt = stmt.where(ConfigurationVersion.tenant_id == tenant_id)
        return list(self.db.execute(stmt).scalars().all())

    def config_completeness_report(
        self, tenant_id: uuid.UUID, required_keys: list[str] | None = None
    ) -> dict[str, Any]:
        configs = self.list_tenant_configurations(tenant_id)
        configured_keys = {c.config_key for c in configs}

        default_required = [
            "agency_name", "agency_npi", "agency_state", "agency_contact_email",
            "billing_provider", "telecom_provider", "cad_enabled",
            "epcr_enabled", "compliance_level", "timezone",
        ]
        required = set(required_keys or default_required)
        missing = sorted(required - configured_keys)

        # Collect validation issues
        stmt = (
            select(ConfigurationValidationIssue)
            .where(
                ConfigurationValidationIssue.tenant_id == tenant_id,
                ConfigurationValidationIssue.resolved.is_(False),
            )
        )
        issues = list(self.db.execute(stmt).scalars().all())

        total = len(required)
        configured = total - len(missing)
        score = int((configured / total) * 100) if total > 0 else 100

        return {
            "tenant_id": str(tenant_id),
            "total_keys": total,
            "configured_keys": configured,
            "missing_keys": missing,
            "validation_issues": [
                {"key": i.config_key, "severity": i.severity, "message": i.message}
                for i in issues
            ],
            "completeness_score": score,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # PART 7: FOUNDER COMMAND CENTER (AGGREGATED)
    # ══════════════════════════════════════════════════════════════════════════

    def founder_command_center_summary(self) -> dict[str, Any]:
        """Cross-tenant aggregated view for founder/platform admin."""

        # Agencies in onboarding
        onboarding_stmt = (
            select(Tenant)
            .where(Tenant.lifecycle_state.in_([
                TenantLifecycleState.TENANT_CREATED,
                TenantLifecycleState.CONFIG_PENDING,
                TenantLifecycleState.IMPLEMENTATION_IN_PROGRESS,
                TenantLifecycleState.READY_FOR_GO_LIVE_REVIEW,
            ]))
        )
        onboarding = list(self.db.execute(onboarding_stmt).scalars().all())
        agencies_onboarding = [
            {"id": str(t.id), "name": t.name, "state": t.lifecycle_state}
            for t in onboarding
        ]

        # Implementation blockers across all tenants
        blocked_stmt = (
            select(
                PlatformImplementationProject.tenant_id,
                func.count(ImplementationBlocker.id).label("open_blockers"),
            )
            .join(
                ImplementationBlocker,
                ImplementationBlocker.project_id == PlatformImplementationProject.id,
            )
            .where(ImplementationBlocker.status == "open")
            .group_by(PlatformImplementationProject.tenant_id)
        )
        blocked_rows = list(self.db.execute(blocked_stmt).all())
        agencies_blocked = [
            {"tenant_id": str(row[0]), "open_blockers": row[1]}
            for row in blocked_rows
        ]

        # Degraded environments
        degraded_stmt = select(Environment).where(Environment.health_status == "degraded")
        degraded_envs = list(self.db.execute(degraded_stmt).scalars().all())
        agencies_degraded = [
            {"env": e.name, "status": e.health_status, "version": e.current_version}
            for e in degraded_envs
        ]

        # Suspended tenants
        suspended_stmt = (
            select(Tenant)
            .where(Tenant.lifecycle_state == TenantLifecycleState.SUSPENDED)
        )
        suspended = list(self.db.execute(suspended_stmt).scalars().all())

        # Failed deployments (recent)
        failed_stmt = (
            select(DeploymentRecord)
            .where(DeploymentRecord.outcome == "failure")
            .order_by(DeploymentRecord.created_at.desc())
            .limit(10)
        )
        failed_deps = list(self.db.execute(failed_stmt).scalars().all())
        failed_deployments = [
            {
                "id": str(d.id),
                "environment_id": str(d.environment_id),
                "release_version_id": str(d.release_version_id),
                "error": d.error_detail,
            }
            for d in failed_deps
        ]

        # Unresolved drift alerts
        drift_stmt = select(ConfigDriftAlert).where(ConfigDriftAlert.resolved.is_(False))
        drifts = list(self.db.execute(drift_stmt).scalars().all())
        config_gaps = [
            {
                "env_id": str(d.environment_id),
                "type": d.drift_type,
                "severity": d.severity,
                "description": d.description,
            }
            for d in drifts
        ]

        live_count = self.db.execute(
            select(func.count(Tenant.id)).where(
                Tenant.lifecycle_state == TenantLifecycleState.LIVE
            )
        ).scalar() or 0

        return {
            "agencies_onboarding": agencies_onboarding,
            "agencies_blocked": agencies_blocked,
            "agencies_degraded": agencies_degraded,
            "user_provisioning_issues": {"suspended_tenants": len(suspended)},
            "role_anomalies": [],
            "feature_mismatches": [],
            "failed_deployments": failed_deployments,
            "config_gaps": config_gaps,
            "top_actions": self._compute_top_actions(
                agencies_onboarding, agencies_blocked, failed_deployments, config_gaps
            ),
            "health_scores": {
                "agencies_live": live_count,
                "agencies_onboarding": len(agencies_onboarding),
                "agencies_suspended": len(suspended),
                "open_blockers": sum(r[1] for r in blocked_rows),
                "degraded_environments": len(agencies_degraded),
                "unresolved_drifts": len(drifts),
                "failed_deployments_recent": len(failed_deps),
            },
        }

    @staticmethod
    def _compute_top_actions(
        onboarding: list[dict[str, Any]],
        blocked: list[dict[str, Any]],
        failed: list[dict[str, Any]],
        drifts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if blocked:
            actions.append({
                "priority": "HIGH",
                "action": "Resolve implementation blockers",
                "count": len(blocked),
            })
        if failed:
            actions.append({
                "priority": "CRITICAL",
                "action": "Investigate failed deployments",
                "count": len(failed),
            })
        if drifts:
            actions.append({
                "priority": "MEDIUM",
                "action": "Resolve configuration drift alerts",
                "count": len(drifts),
            })
        if onboarding:
            actions.append({
                "priority": "MEDIUM",
                "action": "Progress agencies through onboarding",
                "count": len(onboarding),
            })
        return actions
