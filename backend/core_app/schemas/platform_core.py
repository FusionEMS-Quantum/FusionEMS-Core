"""
Pydantic schemas for Platform Core domains:
Tenant Lifecycle, User Provisioning, Implementation, Feature Flags,
Release/Environment, System Configuration, Founder Command Center.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ===========================================================================
# SHARED
# ===========================================================================

class PlatformAuditBase(BaseModel):
    reason: str
    correlation_id: str | None = None


# ===========================================================================
# PART 1: TENANT / AGENCY LIFECYCLE
# ===========================================================================

class TenantLifecycleTransitionRequest(PlatformAuditBase):
    to_state: str


class TenantLifecycleTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tenant_id: uuid.UUID
    from_state: str | None
    to_state: str
    transitioned_at: datetime


class AgencyLifecycleEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    from_state: str | None
    to_state: str
    reason: str
    actor_user_id: uuid.UUID | None
    created_at: datetime


class AgencyImplementationOwnerRequest(BaseModel):
    owner_user_id: uuid.UUID
    role_label: str = "implementation_lead"


class AgencyContractLinkRequest(BaseModel):
    contract_type: str
    external_contract_id: str | None = None
    signed_at: datetime | None = None
    expires_at: datetime | None = None
    metadata_blob: dict[str, Any] = Field(default_factory=dict)


class AgencyContractLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    contract_type: str
    external_contract_id: str | None
    status: str
    signed_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


# ===========================================================================
# PART 2: USER / ACCESS PROVISIONING
# ===========================================================================

class UserInviteRequest(BaseModel):
    email: str
    role: str
    tenant_id: uuid.UUID | None = None


class UserActivateRequest(BaseModel):
    pass


class RoleAssignmentRequest(PlatformAuditBase):
    role_name: str


class RoleRevocationRequest(PlatformAuditBase):
    role_name: str


class UserProvisioningEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    event_type: str
    detail: str
    actor_user_id: uuid.UUID | None
    created_at: datetime


class UserRoleAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role_name: str
    is_active: bool
    assigned_by_user_id: uuid.UUID | None
    created_at: datetime


class UserAccessAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    old_value: str | None
    new_value: str | None
    actor_user_id: uuid.UUID | None
    created_at: datetime


class UserModuleVisibilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    modules: list[dict[str, Any]]


# ===========================================================================
# PART 3: IMPLEMENTATION / ONBOARDING
# ===========================================================================

class ImplementationProjectCreateRequest(BaseModel):
    target_go_live_date: datetime | None = None
    notes: str | None = None


class ImplementationProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    current_state: str
    target_go_live_date: datetime | None
    actual_go_live_date: datetime | None
    owner_user_id: uuid.UUID | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ChecklistItemCreateRequest(BaseModel):
    category: str
    title: str
    description: str | None = None
    is_required: bool = True
    owner_user_id: uuid.UUID | None = None
    sort_order: int = 0


class ChecklistItemUpdateRequest(BaseModel):
    status: str | None = None
    owner_user_id: uuid.UUID | None = None


class ChecklistItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    category: str
    title: str
    description: str | None
    status: str
    is_required: bool
    owner_user_id: uuid.UUID | None
    completed_at: datetime | None
    completed_by_user_id: uuid.UUID | None
    sort_order: int
    created_at: datetime


class BlockerCreateRequest(BaseModel):
    title: str
    description: str
    severity: str = "HIGH"
    owner_user_id: uuid.UUID | None = None


class BlockerResolveRequest(PlatformAuditBase):
    resolution_notes: str


class BlockerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str
    severity: str
    status: str
    owner_user_id: uuid.UUID | None
    resolved_at: datetime | None
    resolved_by_user_id: uuid.UUID | None
    resolution_notes: str | None
    created_at: datetime


class GoLiveApprovalRequest(PlatformAuditBase):
    pass


class GoLiveApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    checklist_snapshot: dict[str, Any]
    blocker_snapshot: dict[str, Any]
    created_at: datetime


class LaunchReadinessReviewRequest(BaseModel):
    overall_score: int
    config_score: int = 0
    billing_score: int = 0
    telecom_score: int = 0
    compliance_score: int = 0
    verdict: str
    notes: str | None = None
    findings: dict[str, Any] = Field(default_factory=dict)


class LaunchReadinessReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    tenant_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    overall_score: int
    config_score: int
    billing_score: int
    telecom_score: int
    compliance_score: int
    verdict: str
    notes: str | None
    findings: dict[str, Any]
    created_at: datetime


class ImplementationStateTransitionRequest(PlatformAuditBase):
    to_state: str


# ===========================================================================
# PART 4: FEATURE FLAGS / MODULE ENTITLEMENT
# ===========================================================================

class FeatureFlagCreateRequest(BaseModel):
    flag_key: str
    display_name: str
    description: str | None = None
    default_state: str = "DISABLED"
    category: str = "general"
    is_critical: bool = False
    requires_billing: bool = False
    environment_scope: str | None = None


class FeatureFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    flag_key: str
    display_name: str
    description: str | None
    default_state: str
    category: str
    is_critical: bool
    requires_billing: bool
    environment_scope: str | None
    version: int
    created_at: datetime


class TenantFeatureStateRequest(PlatformAuditBase):
    state: str
    rollout_percentage: int | None = None
    notes: str | None = None


class TenantFeatureStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    feature_flag_id: uuid.UUID
    current_state: str
    enabled_at: datetime | None
    enabled_by_user_id: uuid.UUID | None
    rollout_percentage: int | None
    notes: str | None
    version: int
    created_at: datetime


class ModuleEntitlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    module_name: str
    plan_code: str
    is_entitled: bool
    billing_status: str
    effective_from: datetime
    effective_until: datetime | None


class EntitlementVsRuntimeReport(BaseModel):
    tenant_id: uuid.UUID
    mismatches: list[dict[str, Any]]
    total_entitled: int
    total_runtime_enabled: int
    drift_detected: bool


class FeatureFlagAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    feature_flag_id: uuid.UUID
    tenant_id: uuid.UUID | None
    action: str
    old_state: str | None
    new_state: str | None
    actor_user_id: uuid.UUID | None
    reason: str | None
    created_at: datetime


# ===========================================================================
# PART 5: RELEASE / ENVIRONMENT CONTROL
# ===========================================================================

class EnvironmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    display_name: str
    status: str
    current_version: str | None
    current_git_sha: str | None
    deployed_at: datetime | None
    health_status: str
    created_at: datetime


class ReleaseVersionCreateRequest(BaseModel):
    version_tag: str
    git_sha: str
    release_notes: str | None = None
    migration_count: int = 0
    created_by: str | None = None


class ReleaseVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    version_tag: str
    git_sha: str
    release_notes: str | None
    migration_count: int
    is_rollback_candidate: bool
    created_by: str | None
    created_at: datetime


class DeploymentRecordCreateRequest(BaseModel):
    environment_id: uuid.UUID
    release_version_id: uuid.UUID
    deployed_by: str


class DeploymentRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    environment_id: uuid.UUID
    release_version_id: uuid.UUID
    current_state: str
    deployed_by: str
    started_at: datetime
    completed_at: datetime | None
    outcome: str | None
    created_at: datetime


class DeploymentValidationRequest(BaseModel):
    validation_type: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    validated_by: str | None = None


class RollbackRequest(PlatformAuditBase):
    to_version_id: uuid.UUID
    initiated_by: str


class ConfigDriftAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    environment_id: uuid.UUID
    drift_type: str
    description: str
    severity: str
    expected_value: str | None
    actual_value: str | None
    resolved: bool
    created_at: datetime


# ===========================================================================
# PART 6: SYSTEM CONFIGURATION
# ===========================================================================

class TenantConfigurationRequest(BaseModel):
    config_key: str
    config_value: dict[str, Any]
    category: str = "general"
    is_sensitive: bool = False


class TenantConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    config_key: str
    config_value: dict[str, Any]
    category: str
    is_sensitive: bool
    version: int
    created_at: datetime
    updated_at: datetime


class SystemConfigurationRequest(BaseModel):
    config_key: str
    config_value: dict[str, Any]
    category: str = "general"
    is_sensitive: bool = False
    environment: str | None = None


class SystemConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    config_key: str
    config_value: dict[str, Any]
    category: str
    is_sensitive: bool
    environment: str | None
    version: int
    created_at: datetime


class ConfigCompletenessReport(BaseModel):
    tenant_id: uuid.UUID
    total_keys: int
    configured_keys: int
    missing_keys: list[str]
    validation_issues: list[dict[str, Any]]
    completeness_score: int


class ConfigurationVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    config_table: str
    config_key: str
    tenant_id: uuid.UUID | None
    version_number: int
    snapshot: dict[str, Any]
    changed_by_user_id: uuid.UUID | None
    change_reason: str | None
    created_at: datetime


# ===========================================================================
# PART 7: FOUNDER COMMAND CENTER AGGREGATED
# ===========================================================================

class FounderCommandCenterSummary(BaseModel):
    agencies_onboarding: list[dict[str, Any]]
    agencies_blocked: list[dict[str, Any]]
    agencies_degraded: list[dict[str, Any]]
    user_provisioning_issues: dict[str, Any]
    role_anomalies: list[dict[str, Any]]
    feature_mismatches: list[dict[str, Any]]
    failed_deployments: list[dict[str, Any]]
    config_gaps: list[dict[str, Any]]
    top_actions: list[dict[str, Any]]
    health_scores: dict[str, int]


# ===========================================================================
# PART 8: PLATFORM ADMIN AI ASSISTANT
# ===========================================================================

class PlatformAdminIssue(BaseModel):
    """Structured AI issue diagnosis in the required 9-field format."""
    issue_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    issue_name: str
    severity: str  # BLOCKING, HIGH, MEDIUM, LOW, INFORMATIONAL
    source: str  # RULE, AI_REVIEW, IMPLEMENTATION_EVENT, DEPLOYMENT_EVENT, CONFIG_EVENT, ACCESS_EVENT, HUMAN_NOTE
    what_is_wrong: str
    why_it_matters: str
    what_you_should_do: str
    platform_context: str
    human_review: str  # REQUIRED, RECOMMENDED, SAFE_TO_AUTO_PROCESS
    confidence: str  # HIGH, MEDIUM, LOW
    basis: str = "OBSERVED"  # OBSERVED, INFERRED, RECOMMENDED
    rule_reference: str | None = None
    domain: str | None = None
