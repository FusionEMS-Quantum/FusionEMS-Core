"""
Platform Core Models — Tenant Lifecycle, User Provisioning, Implementation,
Feature Flags, Release/Environment, System Configuration.

Implements Parts 1-8 of the Master Platform Core Directive.
All models are production-grade with proper enums, state machines, and audit trails.
"""
# pylint: disable=not-callable,unsubscriptable-object
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin

# ===========================================================================
# PART 1: TENANT / AGENCY LIFECYCLE
# ===========================================================================


class TenantLifecycleState(enum.StrEnum):
    TENANT_CREATED = "TENANT_CREATED"
    CONFIG_PENDING = "CONFIG_PENDING"
    IMPLEMENTATION_IN_PROGRESS = "IMPLEMENTATION_IN_PROGRESS"
    READY_FOR_GO_LIVE_REVIEW = "READY_FOR_GO_LIVE_REVIEW"
    LIVE = "LIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class AgencyType(enum.StrEnum):
    EMS = "EMS"
    HEMS = "HEMS"
    FIRE = "FIRE"
    IFT = "IFT"
    COMMUNITY_PARAMEDICINE = "COMMUNITY_PARAMEDICINE"
    INTEGRATED = "INTEGRATED"


class AgencyEnvironmentScope(enum.StrEnum):
    DEV = "DEV"
    STAGING = "STAGING"
    PREPROD = "PREPROD"
    PRODUCTION = "PRODUCTION"


class AgencyLifecycleEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable record of every tenant lifecycle state transition."""
    __tablename__ = "agency_lifecycle_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    from_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_state: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AgencyStatusAudit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Compliance-grade audit of every status change for an agency."""
    __tablename__ = "agency_status_audits"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AgencyImplementationOwner(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks which user is the implementation contact for an agency."""
    __tablename__ = "agency_implementation_owners"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role_label: Mapped[str] = mapped_column(String(64), nullable=False, default="implementation_lead")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class AgencyContractLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Links an agency to a signed contract or agreement."""
    __tablename__ = "agency_contract_links"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    contract_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_contract_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


# ===========================================================================
# PART 2: USER / ACCESS PROVISIONING
# ===========================================================================


class UserAccessState(enum.StrEnum):
    INVITED = "INVITED"
    ACTIVATION_PENDING = "ACTIVATION_PENDING"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    SUSPENDED = "SUSPENDED"
    ACCESS_REVIEW_REQUIRED = "ACCESS_REVIEW_REQUIRED"


class UserProvisioningEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable record of user provisioning actions."""
    __tablename__ = "user_provisioning_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class UserOrgMembership(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit tenant/agency scope for a user."""
    __tablename__ = "user_org_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_org_membership"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserRoleAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Auditable role assignment with history."""
    __tablename__ = "user_role_assignments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserModuleVisibility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Per-user module access visibility based on role AND entitlement."""
    __tablename__ = "user_module_visibility"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    module_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="role")
    overridden_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )


class UserAccessAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit of role changes and access-related mutations."""
    __tablename__ = "user_access_audit_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


# ===========================================================================
# PART 3: IMPLEMENTATION / ONBOARDING
# ===========================================================================


class ImplementationState(enum.StrEnum):
    IMPLEMENTATION_CREATED = "IMPLEMENTATION_CREATED"
    REQUIREMENTS_PENDING = "REQUIREMENTS_PENDING"
    CONFIG_IN_PROGRESS = "CONFIG_IN_PROGRESS"
    BLOCKED = "BLOCKED"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    GO_LIVE_APPROVED = "GO_LIVE_APPROVED"
    GO_LIVE_SCHEDULED = "GO_LIVE_SCHEDULED"
    LIVE_STABILIZATION = "LIVE_STABILIZATION"
    IMPLEMENTATION_COMPLETE = "IMPLEMENTATION_COMPLETE"


class ImplementationProject(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    """Parent project tracking agency implementation/onboarding."""
    __tablename__ = "implementation_projects"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    current_state: Mapped[str] = mapped_column(
        String(64), nullable=False, default=ImplementationState.IMPLEMENTATION_CREATED.value
    )
    target_go_live_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_go_live_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    checklist_items: Mapped[list[ImplementationChecklistItem]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    blockers: Mapped[list[ImplementationBlocker]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ImplementationChecklistItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual checklist item within an implementation project."""
    __tablename__ = "implementation_checklist_items"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("implementation_projects.id"), nullable=False, index=True
    )
    project: Mapped[ImplementationProject] = relationship(back_populates="checklist_items")

    category: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ImplementationBlocker(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit blocker preventing implementation progress."""
    __tablename__ = "implementation_blockers"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("implementation_projects.id"), nullable=False, index=True
    )
    project: Mapped[ImplementationProject] = relationship(back_populates="blockers")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="HIGH")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class GoLiveApproval(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable record of go-live approval decisions."""
    __tablename__ = "go_live_approvals"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("implementation_projects.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    denied_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    blocker_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class LaunchReadinessReview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pre-launch validation review with scores."""
    __tablename__ = "launch_readiness_reviews"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("implementation_projects.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    config_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    billing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    telecom_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compliance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    findings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ImplementationAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit trail for implementation actions."""
    __tablename__ = "implementation_audit_events"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("implementation_projects.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


# ===========================================================================
# PART 4: FEATURE FLAGS / MODULE ENTITLEMENT
# ===========================================================================


class FeatureFlagState(enum.StrEnum):
    DISABLED = "DISABLED"
    ELIGIBLE_NOT_ENABLED = "ELIGIBLE_NOT_ENABLED"
    ENABLED = "ENABLED"
    LIMITED_ROLLOUT = "LIMITED_ROLLOUT"
    BETA_ENABLED = "BETA_ENABLED"
    PAUSED = "PAUSED"
    RETIRED = "RETIRED"


class FeatureFlag(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    """Platform-wide feature flag definition."""
    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("flag_key", name="uq_feature_flag_key"),
    )

    flag_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=FeatureFlagState.DISABLED.value
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_billing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    environment_scope: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class TenantFeatureState(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    """Per-tenant runtime state for a feature flag."""
    __tablename__ = "tenant_feature_states"
    __table_args__ = (
        UniqueConstraint("tenant_id", "feature_flag_id", name="uq_tenant_feature_state"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    feature_flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feature_flags.id"), nullable=False, index=True
    )
    current_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=FeatureFlagState.DISABLED.value
    )
    enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    rollout_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ModuleEntitlement(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    """Billing-level module entitlement for a tenant (separate from runtime flags)."""
    __tablename__ = "module_entitlements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "module_name", name="uq_module_entitlement"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    module_name: Mapped[str] = mapped_column(String(64), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    is_entitled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    billing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RolloutDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit record capturing why a rollout decision was made."""
    __tablename__ = "rollout_decisions"

    feature_flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feature_flags.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    rollout_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    environment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class FeatureFlagAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit of feature flag changes."""
    __tablename__ = "feature_flag_audit_events"

    feature_flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("feature_flags.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    old_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ModuleActivationEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable record of module activation/deactivation."""
    __tablename__ = "module_activation_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    module_name: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approval_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("protected_action_approvals.id"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


# ===========================================================================
# PART 5: RELEASE / ENVIRONMENT CONTROL
# ===========================================================================


class EnvironmentName(enum.StrEnum):
    DEV = "DEV"
    STAGING = "STAGING"
    PREPROD = "PREPROD"
    PRODUCTION = "PRODUCTION"


class ReleaseState(enum.StrEnum):
    BUILD_READY = "BUILD_READY"
    DEPLOY_PENDING = "DEPLOY_PENDING"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    VALIDATION_PENDING = "VALIDATION_PENDING"
    VALIDATED = "VALIDATED"
    DEGRADED = "DEGRADED"
    ROLLBACK_PENDING = "ROLLBACK_PENDING"
    ROLLED_BACK = "ROLLED_BACK"


class Environment(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    """Platform environment registry."""
    __tablename__ = "environments"
    __table_args__ = (
        UniqueConstraint("name", name="uq_environment_name"),
    )

    name: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="operational")
    current_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    current_git_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class ReleaseVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks a versioned release of the platform."""
    __tablename__ = "release_versions"

    version_tag: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    git_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    migration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_rollback_candidate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class DeploymentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Records every deployment to an environment."""
    __tablename__ = "deployment_records"

    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), nullable=False, index=True
    )
    release_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("release_versions.id"), nullable=False
    )
    current_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReleaseState.DEPLOY_PENDING.value
    )
    deployed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class DeploymentValidation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Separate validation record for a deployment (validation != deploy)."""
    __tablename__ = "deployment_validations"

    deployment_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deployment_records.id"), nullable=False, index=True
    )
    validation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    validated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


class RollbackRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Records rollback operations."""
    __tablename__ = "rollback_records"

    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), nullable=False, index=True
    )
    from_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("release_versions.id"), nullable=False
    )
    to_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("release_versions.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConfigDriftAlert(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Alerts for configuration drift between environments."""
    __tablename__ = "config_drift_alerts"

    environment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), nullable=False, index=True
    )
    drift_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM")
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReleaseAuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit of release/deployment events."""
    __tablename__ = "release_audit_events"

    environment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environments.id"), nullable=True
    )
    release_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("release_versions.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_blob: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


# ===========================================================================
# PART 6: SYSTEM CONFIGURATION
# ===========================================================================


class TenantConfiguration(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    """Structured, auditable per-tenant configuration."""
    __tablename__ = "tenant_configurations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "config_key", name="uq_tenant_config_key"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    config_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)


class SystemConfiguration(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    """Platform-wide system configuration (not tenant-specific)."""
    __tablename__ = "system_configurations"
    __table_args__ = (
        UniqueConstraint("config_key", name="uq_system_config_key"),
    )

    config_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    config_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    environment: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ConfigurationVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Explicit configuration version history snapshot."""
    __tablename__ = "configuration_versions"

    config_table: Mapped[str] = mapped_column(String(64), nullable=False)
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConfigurationChangeAudit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit of configuration changes."""
    __tablename__ = "configuration_change_audits"

    config_table: Mapped[str] = mapped_column(String(64), nullable=False)
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ConfigurationValidationIssue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks configuration validation issues/warnings."""
    __tablename__ = "configuration_validation_issues"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
