# pylint: disable=unused-argument

"""
Platform Core API Router — Tenant lifecycle, user provisioning, implementation,
feature flags, release/environment, system configuration, founder command center.

All endpoints use RBAC (require_role), tenant scoping, structured error responses.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    require_role,
)
from core_app.core.config import (
    get_settings,
    is_placeholder_config_value,
    is_valid_entra_tenant_identifier,
)
from core_app.schemas.auth import CurrentUser
from core_app.schemas.platform_core import (
    AgencyContractLinkRequest,
    AgencyContractLinkResponse,
    AgencyImplementationOwnerRequest,
    AgencyLifecycleEventResponse,
    BlockerCreateRequest,
    BlockerResolveRequest,
    BlockerResponse,
    ChecklistItemCreateRequest,
    ChecklistItemResponse,
    ChecklistItemUpdateRequest,
    ConfigCompletenessReport,
    ConfigDriftAlertResponse,
    ConfigurationVersionResponse,
    DeploymentRecordCreateRequest,
    DeploymentRecordResponse,
    DeploymentValidationRequest,
    EntitlementVsRuntimeReport,
    EnvironmentResponse,
    FeatureFlagCreateRequest,
    FeatureFlagResponse,
    FounderCommandCenterSummary,
    GoLiveApprovalRequest,
    GoLiveApprovalResponse,
    ImplementationProjectCreateRequest,
    ImplementationProjectResponse,
    ImplementationStateTransitionRequest,
    LaunchReadinessReviewRequest,
    LaunchReadinessReviewResponse,
    ModuleEntitlementResponse,
    PlatformAdminIssue,
    ReleaseVersionCreateRequest,
    ReleaseVersionResponse,
    RoleAssignmentRequest,
    RoleRevocationRequest,
    RollbackRequest,
    SystemConfigurationRequest,
    SystemConfigurationResponse,
    TenantConfigurationRequest,
    TenantConfigurationResponse,
    TenantFeatureStateRequest,
    TenantFeatureStateResponse,
    TenantLifecycleTransitionRequest,
    TenantLifecycleTransitionResponse,
    UserInviteRequest,
    UserProvisioningEventResponse,
    UserRoleAssignmentResponse,
)
from core_app.services.ai_platform.platform_admin_assistant_service import (
    PlatformAdminAssistantService,
)
from core_app.services.platform_core_service import PlatformCoreService

router = APIRouter(prefix="/api/v1/platform", tags=["Platform Core"])


def _svc(db: Session) -> PlatformCoreService:
    return PlatformCoreService(db)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_artifact_json(relative_path: str) -> dict[str, object] | None:
    repo_root = _repo_root().resolve()
    artifact_path = (repo_root / relative_path).resolve()
    if not artifact_path.is_relative_to(repo_root):
        return None
    if not artifact_path.exists() or not artifact_path.is_file():
        return None
    try:
        return json.loads(artifact_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1: TENANT / AGENCY LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/tenants/{tenant_id}/lifecycle/transition", response_model=TenantLifecycleTransitionResponse)
def transition_tenant_lifecycle(
    tenant_id: UUID,
    payload: TenantLifecycleTransitionRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> TenantLifecycleTransitionResponse:
    svc = _svc(db)
    tenant = svc.transition_tenant_lifecycle(
        tenant_id=tenant_id,
        actor_user_id=current.user_id,
        to_state=payload.to_state,
        reason=payload.reason,
        correlation_id=payload.correlation_id,
    )
    db.commit()
    return TenantLifecycleTransitionResponse(
        tenant_id=tenant.id,
        from_state=None,
        to_state=tenant.lifecycle_state,
        transitioned_at=tenant.updated_at,
    )


@router.get("/tenants/{tenant_id}/lifecycle/events", response_model=list[AgencyLifecycleEventResponse])
def list_lifecycle_events(
    tenant_id: UUID,
    limit: int = Query(default=100, le=500),
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[AgencyLifecycleEventResponse]:
    svc = _svc(db)
    events = svc.list_lifecycle_events(tenant_id, limit=limit)
    return [AgencyLifecycleEventResponse.model_validate(e) for e in events]


@router.post("/tenants/{tenant_id}/implementation-owners")
def assign_implementation_owner(
    tenant_id: UUID,
    payload: AgencyImplementationOwnerRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    svc = _svc(db)
    rec = svc.assign_implementation_owner(
        tenant_id=tenant_id,
        owner_user_id=payload.owner_user_id,
        assigned_by_user_id=current.user_id,
        role_label=payload.role_label,
    )
    db.commit()
    return {"id": str(rec.id), "status": "assigned"}


@router.post("/tenants/{tenant_id}/contracts", response_model=AgencyContractLinkResponse)
def create_contract_link(
    tenant_id: UUID,
    payload: AgencyContractLinkRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> AgencyContractLinkResponse:
    svc = _svc(db)
    rec = svc.create_contract_link(
        tenant_id=tenant_id,
        contract_type=payload.contract_type,
        external_contract_id=payload.external_contract_id,
        signed_at=payload.signed_at,
        expires_at=payload.expires_at,
        metadata_blob=payload.metadata_blob,
    )
    db.commit()
    return AgencyContractLinkResponse.model_validate(rec)


@router.get("/tenants/{tenant_id}/contracts", response_model=list[AgencyContractLinkResponse])
def list_contract_links(
    tenant_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[AgencyContractLinkResponse]:
    svc = _svc(db)
    links = svc.list_contract_links(tenant_id)
    return [AgencyContractLinkResponse.model_validate(lnk) for lnk in links]


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2: USER / ACCESS PROVISIONING
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/users/invite")
def invite_user(
    payload: UserInviteRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    svc = _svc(db)
    target_tenant = payload.tenant_id or current.tenant_id
    user = svc.invite_user(
        tenant_id=target_tenant,
        email=payload.email,
        role=payload.role,
        actor_user_id=current.user_id,
    )
    db.commit()
    return {"user_id": str(user.id), "email": user.email, "status": user.status}


@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    svc = _svc(db)
    user = svc.activate_user(current.tenant_id, user_id, current.user_id)
    db.commit()
    return {"user_id": str(user.id), "status": user.status}


@router.post("/users/{user_id}/disable")
def disable_user(
    user_id: UUID,
    payload: RoleRevocationRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    svc = _svc(db)
    user = svc.disable_user(
        current.tenant_id, user_id, current.user_id,
        reason=payload.reason,
        correlation_id=payload.correlation_id,
    )
    db.commit()
    return {"user_id": str(user.id), "status": user.status}


@router.post("/users/{user_id}/roles", response_model=UserRoleAssignmentResponse)
def assign_role(
    user_id: UUID,
    payload: RoleAssignmentRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> UserRoleAssignmentResponse:
    svc = _svc(db)
    assignment = svc.assign_role(
        tenant_id=current.tenant_id,
        user_id=user_id,
        role_name=payload.role_name,
        actor_user_id=current.user_id,
        reason=payload.reason,
        correlation_id=payload.correlation_id,
    )
    db.commit()
    return UserRoleAssignmentResponse.model_validate(assignment)


@router.delete("/users/{user_id}/roles/{role_name}")
def revoke_role(
    user_id: UUID,
    role_name: str,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    svc = _svc(db)
    svc.revoke_role(
        tenant_id=current.tenant_id,
        user_id=user_id,
        role_name=role_name,
        actor_user_id=current.user_id,
        reason="Revoked via platform admin",
    )
    db.commit()
    return {"status": "revoked"}


@router.get("/users/{user_id}/roles", response_model=list[UserRoleAssignmentResponse])
def list_user_roles(
    user_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[UserRoleAssignmentResponse]:
    svc = _svc(db)
    roles = svc.list_user_roles(current.tenant_id, user_id)
    return [UserRoleAssignmentResponse.model_validate(r) for r in roles]


@router.get("/users/provisioning-events", response_model=list[UserProvisioningEventResponse])
def list_provisioning_events(
    user_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[UserProvisioningEventResponse]:
    svc = _svc(db)
    events = svc.list_provisioning_events(current.tenant_id, user_id=user_id, limit=limit)
    return [UserProvisioningEventResponse.model_validate(e) for e in events]


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3: IMPLEMENTATION / ONBOARDING
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/implementations", response_model=ImplementationProjectResponse)
def create_implementation(
    payload: ImplementationProjectCreateRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ImplementationProjectResponse:
    svc = _svc(db)
    project = svc.create_implementation_project(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        target_go_live_date=payload.target_go_live_date,
        notes=payload.notes,
    )
    db.commit()
    return ImplementationProjectResponse.model_validate(project)


@router.get("/implementations", response_model=list[ImplementationProjectResponse])
def list_implementations(
    state: str | None = Query(default=None),
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[ImplementationProjectResponse]:
    svc = _svc(db)
    projects = svc.list_implementation_projects(current.tenant_id, state=state)
    return [ImplementationProjectResponse.model_validate(p) for p in projects]


@router.get("/implementations/{project_id}", response_model=ImplementationProjectResponse)
def get_implementation(
    project_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ImplementationProjectResponse:
    svc = _svc(db)
    project = svc.get_implementation_project(current.tenant_id, project_id)
    return ImplementationProjectResponse.model_validate(project)


@router.post("/implementations/{project_id}/transition", response_model=ImplementationProjectResponse)
def transition_implementation(
    project_id: UUID,
    payload: ImplementationStateTransitionRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ImplementationProjectResponse:
    svc = _svc(db)
    project = svc.transition_implementation_state(
        tenant_id=current.tenant_id,
        project_id=project_id,
        actor_user_id=current.user_id,
        to_state=payload.to_state,
        reason=payload.reason,
        correlation_id=payload.correlation_id,
    )
    db.commit()
    return ImplementationProjectResponse.model_validate(project)


@router.post(
    "/implementations/{project_id}/checklist",
    response_model=ChecklistItemResponse,
)
def add_checklist_item(
    project_id: UUID,
    payload: ChecklistItemCreateRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ChecklistItemResponse:
    svc = _svc(db)
    item = svc.add_checklist_item(
        tenant_id=current.tenant_id,
        project_id=project_id,
        actor_user_id=current.user_id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        is_required=payload.is_required,
        owner_user_id=payload.owner_user_id,
        sort_order=payload.sort_order,
    )
    db.commit()
    return ChecklistItemResponse.model_validate(item)


@router.get("/implementations/{project_id}/checklist", response_model=list[ChecklistItemResponse])
def list_checklist_items(
    project_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[ChecklistItemResponse]:
    svc = _svc(db)
    items = svc.list_checklist_items(current.tenant_id, project_id)
    return [ChecklistItemResponse.model_validate(i) for i in items]


@router.patch(
    "/implementations/{project_id}/checklist/{item_id}",
    response_model=ChecklistItemResponse,
)
def update_checklist_item(
    project_id: UUID,
    item_id: UUID,
    payload: ChecklistItemUpdateRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ChecklistItemResponse:
    svc = _svc(db)
    item = svc.update_checklist_item(
        tenant_id=current.tenant_id,
        project_id=project_id,
        item_id=item_id,
        actor_user_id=current.user_id,
        status=payload.status,
        owner_user_id=payload.owner_user_id,
    )
    db.commit()
    return ChecklistItemResponse.model_validate(item)


@router.post(
    "/implementations/{project_id}/blockers",
    response_model=BlockerResponse,
)
def add_blocker(
    project_id: UUID,
    payload: BlockerCreateRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> BlockerResponse:
    svc = _svc(db)
    blocker = svc.add_blocker(
        tenant_id=current.tenant_id,
        project_id=project_id,
        actor_user_id=current.user_id,
        title=payload.title,
        description=payload.description,
        severity=payload.severity,
        owner_user_id=payload.owner_user_id,
    )
    db.commit()
    return BlockerResponse.model_validate(blocker)


@router.get("/implementations/{project_id}/blockers", response_model=list[BlockerResponse])
def list_blockers(
    project_id: UUID,
    status: str | None = Query(default=None),
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[BlockerResponse]:
    svc = _svc(db)
    blockers = svc.list_blockers(current.tenant_id, project_id, status=status)
    return [BlockerResponse.model_validate(b) for b in blockers]


@router.post(
    "/implementations/{project_id}/blockers/{blocker_id}/resolve",
    response_model=BlockerResponse,
)
def resolve_blocker(
    project_id: UUID,
    blocker_id: UUID,
    payload: BlockerResolveRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> BlockerResponse:
    svc = _svc(db)
    blocker = svc.resolve_blocker(
        tenant_id=current.tenant_id,
        project_id=project_id,
        blocker_id=blocker_id,
        actor_user_id=current.user_id,
        resolution_notes=payload.resolution_notes,
        reason=payload.reason,
    )
    db.commit()
    return BlockerResponse.model_validate(blocker)


@router.post(
    "/implementations/{project_id}/go-live/request",
    response_model=GoLiveApprovalResponse,
)
def request_go_live(
    project_id: UUID,
    payload: GoLiveApprovalRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> GoLiveApprovalResponse:
    svc = _svc(db)
    approval = svc.request_go_live_approval(
        tenant_id=current.tenant_id,
        project_id=project_id,
        actor_user_id=current.user_id,
        reason=payload.reason,
    )
    db.commit()
    return GoLiveApprovalResponse.model_validate(approval)


@router.post(
    "/implementations/{project_id}/go-live/{approval_id}/approve",
    response_model=GoLiveApprovalResponse,
)
def approve_go_live(
    project_id: UUID,
    approval_id: UUID,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> GoLiveApprovalResponse:
    svc = _svc(db)
    approval = svc.approve_go_live(
        tenant_id=current.tenant_id,
        project_id=project_id,
        approval_id=approval_id,
        actor_user_id=current.user_id,
    )
    db.commit()
    return GoLiveApprovalResponse.model_validate(approval)


@router.post(
    "/implementations/{project_id}/readiness-review",
    response_model=LaunchReadinessReviewResponse,
)
def create_readiness_review(
    project_id: UUID,
    payload: LaunchReadinessReviewRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> LaunchReadinessReviewResponse:
    svc = _svc(db)
    review = svc.create_launch_readiness_review(
        tenant_id=current.tenant_id,
        project_id=project_id,
        reviewer_user_id=current.user_id,
        overall_score=payload.overall_score,
        verdict=payload.verdict,
        config_score=payload.config_score,
        billing_score=payload.billing_score,
        telecom_score=payload.telecom_score,
        compliance_score=payload.compliance_score,
        notes=payload.notes,
        findings=payload.findings,
    )
    db.commit()
    return LaunchReadinessReviewResponse.model_validate(review)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4: FEATURE FLAGS / MODULE ENTITLEMENT
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/feature-flags", response_model=FeatureFlagResponse)
def create_feature_flag(
    payload: FeatureFlagCreateRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> FeatureFlagResponse:
    svc = _svc(db)
    flag = svc.create_feature_flag(
        actor_user_id=current.user_id,
        flag_key=payload.flag_key,
        display_name=payload.display_name,
        description=payload.description,
        default_state=payload.default_state,
        category=payload.category,
        is_critical=payload.is_critical,
        requires_billing=payload.requires_billing,
        environment_scope=payload.environment_scope,
    )
    db.commit()
    return FeatureFlagResponse.model_validate(flag)


@router.get("/feature-flags", response_model=list[FeatureFlagResponse])
def list_feature_flags(
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[FeatureFlagResponse]:
    svc = _svc(db)
    flags = svc.list_feature_flags()
    return [FeatureFlagResponse.model_validate(f) for f in flags]


@router.post(
    "/feature-flags/{flag_id}/tenants/{tenant_id}",
    response_model=TenantFeatureStateResponse,
)
def set_tenant_feature_state(
    flag_id: UUID,
    tenant_id: UUID,
    payload: TenantFeatureStateRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> TenantFeatureStateResponse:
    svc = _svc(db)
    tfs = svc.set_tenant_feature_state(
        tenant_id=tenant_id,
        feature_flag_id=flag_id,
        actor_user_id=current.user_id,
        state=payload.state,
        reason=payload.reason,
        rollout_percentage=payload.rollout_percentage,
        notes=payload.notes,
        correlation_id=payload.correlation_id,
    )
    db.commit()
    return TenantFeatureStateResponse.model_validate(tfs)


@router.get(
    "/tenants/{tenant_id}/feature-states",
    response_model=list[TenantFeatureStateResponse],
)
def list_tenant_feature_states(
    tenant_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[TenantFeatureStateResponse]:
    svc = _svc(db)
    states = svc.list_tenant_feature_states(tenant_id)
    return [TenantFeatureStateResponse.model_validate(s) for s in states]


@router.get(
    "/tenants/{tenant_id}/module-entitlements",
    response_model=list[ModuleEntitlementResponse],
)
def list_module_entitlements(
    tenant_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[ModuleEntitlementResponse]:
    svc = _svc(db)
    ents = svc.list_module_entitlements(tenant_id)
    return [ModuleEntitlementResponse.model_validate(e) for e in ents]


@router.get(
    "/tenants/{tenant_id}/entitlement-vs-runtime",
    response_model=EntitlementVsRuntimeReport,
)
def entitlement_vs_runtime(
    tenant_id: UUID,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> EntitlementVsRuntimeReport:
    svc = _svc(db)
    report = svc.entitlement_vs_runtime_report(tenant_id)
    return EntitlementVsRuntimeReport(**report)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5: RELEASE / ENVIRONMENT CONTROL
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/environments", response_model=list[EnvironmentResponse])
def list_environments(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> list[EnvironmentResponse]:
    svc = _svc(db)
    envs = svc.list_environments()
    return [EnvironmentResponse.model_validate(e) for e in envs]


@router.post("/releases", response_model=ReleaseVersionResponse)
def create_release(
    payload: ReleaseVersionCreateRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> ReleaseVersionResponse:
    svc = _svc(db)
    release = svc.create_release_version(
        actor=str(current.user_id),
        version_tag=payload.version_tag,
        git_sha=payload.git_sha,
        release_notes=payload.release_notes,
        migration_count=payload.migration_count,
        created_by=payload.created_by,
    )
    db.commit()
    return ReleaseVersionResponse.model_validate(release)


@router.get("/releases", response_model=list[ReleaseVersionResponse])
def list_releases(
    limit: int = Query(default=50, le=200),
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> list[ReleaseVersionResponse]:
    svc = _svc(db)
    releases = svc.list_release_versions(limit=limit)
    return [ReleaseVersionResponse.model_validate(r) for r in releases]


@router.post("/deployments", response_model=DeploymentRecordResponse)
def create_deployment(
    payload: DeploymentRecordCreateRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> DeploymentRecordResponse:
    svc = _svc(db)
    rec = svc.create_deployment_record(
        actor=str(current.user_id),
        environment_id=payload.environment_id,
        release_version_id=payload.release_version_id,
        deployed_by=payload.deployed_by,
    )
    db.commit()
    return DeploymentRecordResponse.model_validate(rec)


@router.post("/deployments/{deployment_id}/complete", response_model=DeploymentRecordResponse)
def complete_deployment(
    deployment_id: UUID,
    outcome: str = Query(...),
    error_detail: str | None = Query(default=None),
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> DeploymentRecordResponse:
    svc = _svc(db)
    rec = svc.complete_deployment(
        deployment_id=deployment_id,
        actor=str(current.user_id),
        outcome=outcome,
        error_detail=error_detail,
    )
    db.commit()
    return DeploymentRecordResponse.model_validate(rec)


@router.post("/deployments/{deployment_id}/validations")
def add_deployment_validation(
    deployment_id: UUID,
    payload: DeploymentValidationRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    svc = _svc(db)
    val = svc.add_deployment_validation(
        deployment_id=deployment_id,
        validation_type=payload.validation_type,
        status=payload.status,
        details=payload.details,
        validated_by=payload.validated_by,
    )
    db.commit()
    return {"id": str(val.id), "status": val.status}


@router.post("/environments/{env_id}/rollback")
def rollback_environment(
    env_id: UUID,
    payload: RollbackRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    svc = _svc(db)
    env = svc.get_environment(env_id)
    # Determine current version
    from sqlalchemy import select as sa_select

    from core_app.models.platform_core import ReleaseVersion

    current_ver_stmt = sa_select(ReleaseVersion).where(
        ReleaseVersion.version_tag == env.current_version
    )
    current_release = db.execute(current_ver_stmt).scalar_one_or_none()
    from_version_id = current_release.id if current_release else payload.to_version_id

    rec = svc.create_rollback(
        environment_id=env_id,
        from_version_id=from_version_id,
        to_version_id=payload.to_version_id,
        reason=payload.reason,
        initiated_by=payload.initiated_by,
    )
    db.commit()
    return {"id": str(rec.id), "status": rec.status}


@router.get("/config-drift-alerts", response_model=list[ConfigDriftAlertResponse])
def list_drift_alerts(
    environment_id: UUID | None = Query(default=None),
    resolved: bool | None = Query(default=None),
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> list[ConfigDriftAlertResponse]:
    svc = _svc(db)
    alerts = svc.list_config_drift_alerts(environment_id=environment_id, resolved=resolved)
    return [ConfigDriftAlertResponse.model_validate(a) for a in alerts]


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6: SYSTEM CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════


@router.put("/tenants/{tenant_id}/config", response_model=TenantConfigurationResponse)
def set_tenant_config(
    tenant_id: UUID,
    payload: TenantConfigurationRequest,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> TenantConfigurationResponse:
    svc = _svc(db)
    config = svc.set_tenant_configuration(
        tenant_id=tenant_id,
        config_key=payload.config_key,
        config_value=payload.config_value,
        actor_user_id=current.user_id,
        category=payload.category,
        is_sensitive=payload.is_sensitive,
    )
    db.commit()
    return TenantConfigurationResponse.model_validate(config)


@router.get("/tenants/{tenant_id}/config", response_model=list[TenantConfigurationResponse])
def list_tenant_configs(
    tenant_id: UUID,
    category: str | None = Query(default=None),
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[TenantConfigurationResponse]:
    svc = _svc(db)
    configs = svc.list_tenant_configurations(tenant_id, category=category)
    return [TenantConfigurationResponse.model_validate(c) for c in configs]


@router.get("/tenants/{tenant_id}/config/completeness", response_model=ConfigCompletenessReport)
def config_completeness(
    tenant_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> ConfigCompletenessReport:
    svc = _svc(db)
    report = svc.config_completeness_report(tenant_id)
    return ConfigCompletenessReport(**report)


@router.put("/system-config", response_model=SystemConfigurationResponse)
def set_system_config(
    payload: SystemConfigurationRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> SystemConfigurationResponse:
    svc = _svc(db)
    config = svc.set_system_configuration(
        config_key=payload.config_key,
        config_value=payload.config_value,
        actor_user_id=current.user_id,
        category=payload.category,
        is_sensitive=payload.is_sensitive,
        environment=payload.environment,
    )
    db.commit()
    return SystemConfigurationResponse.model_validate(config)


@router.get("/system-config", response_model=list[SystemConfigurationResponse])
def list_system_configs(
    category: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> list[SystemConfigurationResponse]:
    svc = _svc(db)
    configs = svc.list_system_configurations(category=category, environment=environment)
    return [SystemConfigurationResponse.model_validate(c) for c in configs]


@router.get(
    "/config-versions/{config_key}",
    response_model=list[ConfigurationVersionResponse],
)
def config_version_history(
    config_key: str,
    tenant_id: UUID | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[ConfigurationVersionResponse]:
    svc = _svc(db)
    versions = svc.get_config_version_history(config_key, tenant_id=tenant_id, limit=limit)
    return [ConfigurationVersionResponse.model_validate(v) for v in versions]


# ═══════════════════════════════════════════════════════════════════════════════
# PART 7: FOUNDER COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/founder/command-center", response_model=FounderCommandCenterSummary)
def founder_command_center(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> FounderCommandCenterSummary:
    svc = _svc(db)
    summary = svc.founder_command_center_summary()
    return FounderCommandCenterSummary(**summary)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 8: AI PLATFORM ADMIN ASSISTANT
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/ai/diagnose", response_model=list[PlatformAdminIssue])
def ai_diagnose_platform(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> list[PlatformAdminIssue]:
    assistant = PlatformAdminAssistantService(db)
    return assistant.diagnose_platform()


@router.get("/ai/diagnose/{tenant_id}", response_model=list[PlatformAdminIssue])
def ai_diagnose_tenant(
    tenant_id: UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> list[PlatformAdminIssue]:
    assistant = PlatformAdminAssistantService(db)
    return assistant.diagnose_tenant(tenant_id)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 9: RELEASE READINESS GATE
# ═══════════════════════════════════════════════════════════════════════════════


class _GateCheck:
    """Individual gate check result."""

    def __init__(self, name: str, passed: bool, detail: str = "") -> None:
        self.name = name
        self.passed = passed
        self.detail = detail

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def _env_bool(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _release_metadata() -> dict[str, object]:
    version = (
        os.getenv("RELEASE_VERSION")
        or os.getenv("APP_VERSION")
        or os.getenv("BUILD_VERSION")
        or "unknown"
    )
    git_sha = (
        os.getenv("RELEASE_GIT_SHA")
        or os.getenv("GIT_SHA")
        or os.getenv("COMMIT_SHA")
        or ""
    )
    deployment_id = os.getenv("DEPLOYMENT_ID") or os.getenv("AMPLIFY_JOB_ID") or ""
    last_successful_release = (
        os.getenv("LAST_SUCCESSFUL_RELEASE_AT")
        or os.getenv("LAST_SUCCESSFUL_RELEASE")
        or ""
    )
    rollback_ready = _env_bool("ROLLBACK_READY", default=False)
    return {
        "version": version,
        "git_sha": git_sha,
        "deployment_id": deployment_id,
        "last_successful_release": last_successful_release,
        "rollback_ready": rollback_ready,
    }


def _auth_health_snapshot() -> tuple[dict[str, object], list[str]]:
    settings = get_settings()

    graph_required = {
        "GRAPH_TENANT_ID": settings.graph_tenant_id,
        "GRAPH_CLIENT_ID": settings.graph_client_id,
        "GRAPH_CLIENT_SECRET": settings.graph_client_secret,
        "MICROSOFT_REDIRECT_URI": settings.microsoft_redirect_uri,
    }
    missing_graph = [k for k, v in graph_required.items() if not str(v or "").strip()]
    placeholder_graph = [
        k for k, v in graph_required.items() if str(v or "").strip() and is_placeholder_config_value(str(v))
    ]
    tenant_valid = is_valid_entra_tenant_identifier(settings.graph_tenant_id)
    authority_url = (
        f"https://login.microsoftonline.com/{settings.graph_tenant_id}/v2.0/.well-known/openid-configuration"
        if str(settings.graph_tenant_id or "").strip()
        else ""
    )

    microsoft_signin_healthy = (
        len(missing_graph) == 0
        and len(placeholder_graph) == 0
        and tenant_valid
        and authority_url != ""
    )

    auth_mode = str(settings.auth_mode or "").strip().lower()
    environment = str(settings.environment or "").strip().lower()
    cognito_expected = False
    cognito_ready = auth_mode != "cognito" or all(
        [
            str(settings.cognito_region or "").strip(),
            str(settings.cognito_user_pool_id or "").strip(),
            str(settings.cognito_app_client_id or "").strip(),
            str(settings.cognito_issuer or "").strip(),
        ]
    )

    blockers: list[str] = []
    if missing_graph:
        blockers.append(
            "Microsoft Entra auth missing required configuration: " + ", ".join(missing_graph)
        )
    if placeholder_graph:
        blockers.append(
            "Microsoft Entra auth contains placeholder values: " + ", ".join(placeholder_graph)
        )
    if not tenant_valid:
        blockers.append("Microsoft Entra tenant identifier is invalid")
    if auth_mode in {"", "local", "cognito"}:
        blockers.append("AUTH_MODE must be set to fusion_jwt for browser sessions")
    if not cognito_ready:
        blockers.append("Cognito auth path is incomplete for configured auth mode")

    return (
        {
            "environment": environment,
            "auth_mode": auth_mode,
            "microsoft": {
                "healthy": microsoft_signin_healthy,
                "authority": authority_url,
                "tenant_valid": tenant_valid,
                "missing": missing_graph,
                "placeholder_fields": placeholder_graph,
            },
            "cognito": {
                "expected": cognito_expected,
                "ready": bool(cognito_ready),
                "user_pool_id_present": bool(str(settings.cognito_user_pool_id or "").strip()),
                "client_id_present": bool(str(settings.cognito_app_client_id or "").strip()),
                "issuer_present": bool(str(settings.cognito_issuer or "").strip()),
            },
        },
        blockers,
    )


@router.get("/live-status")
def live_status(
    current: CurrentUser = Depends(require_role("founder", "admin", "agency_admin")),
    db: Session = Depends(db_session_dependency),
) -> dict[str, object]:
    """Canonical NOC-style live status for command operations and release decisions."""
    _ = current
    from sqlalchemy import text as sa_text

    settings = get_settings()
    auth_snapshot, auth_blockers = _auth_health_snapshot()
    release = _release_metadata()
    nemsis_report = _load_artifact_json("artifacts/nemsis-ci-report.json") or {}
    neris_report = _load_artifact_json("artifacts/neris-ci-report.json") or {}

    db_ok = True
    try:
        db.execute(sa_text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_state = "not_configured"
    if str(settings.redis_url or "").strip():
        try:
            import redis

            redis.from_url(settings.redis_url, socket_connect_timeout=2).ping()
            redis_state = "healthy"
        except Exception:
            redis_state = "degraded"

    active_incidents = 0
    try:
        active_incidents = int(
            db.execute(
                sa_text(
                    "SELECT count(*) FROM system_alerts "
                    "WHERE data->>'status' = 'active' "
                    "AND (data->>'severity' IN ('critical', 'error', 'high'))"
                )
            ).scalar()
            or 0
        )
    except Exception:
        active_incidents = 0

    integration_state = settings.integration_state_table()
    required_missing: list[str] = []
    for key, state in integration_state.items():
        if bool(state.get("required")) and not bool(state.get("configured")):
            missing = state.get("missing")
            placeholder_fields = state.get("placeholder_fields")
            if isinstance(missing, list):
                required_missing.extend([f"{key}:{item}" for item in missing])
            elif missing:
                required_missing.append(key)
            if isinstance(placeholder_fields, list):
                required_missing.extend([f"{key}:{item}" for item in placeholder_fields])

    telnyx_central_number = "+1-888-365-0144"
    configured_number = str(settings.central_billing_phone_e164 or "").strip()
    telnyx_blockers: list[str] = []
    if configured_number != telnyx_central_number:
        telnyx_blockers.append(f"Central billing number must be {telnyx_central_number}")
    if not str(settings.telnyx_api_key or "").strip():
        telnyx_blockers.append("TELNYX_API_KEY missing")
    if not str(settings.telnyx_messaging_profile_id or "").strip():
        telnyx_blockers.append("TELNYX_MESSAGING_PROFILE_ID missing")
    telnyx_ready = len(telnyx_blockers) == 0

    release_blockers: list[str] = []
    release_blockers.extend(auth_blockers)
    release_blockers.extend(telnyx_blockers)
    if not db_ok:
        release_blockers.append("Database health probe failed")
    if release.get("version") == "unknown":
        release_blockers.append("Release version metadata is missing")
    if not bool(release.get("rollback_ready")):
        release_blockers.append("Rollback readiness flag is not set")
    if required_missing:
        release_blockers.append(
            "Required integration wiring missing: " + ", ".join(sorted(required_missing))
        )

    frontend_signal = str(os.getenv("FRONTEND_HEALTH", "unknown")).strip().lower()
    frontend_status = (
        "healthy"
        if frontend_signal in {"healthy", "ok", "green"}
        else "degraded"
        if frontend_signal in {"degraded", "warn", "yellow", "red", "down"}
        else "unknown"
    )

    services = [
        {"service": "frontend", "status": frontend_status},
        {"service": "backend", "status": "healthy" if db_ok else "degraded"},
        {
            "service": "auth",
            "status": "healthy" if len(auth_blockers) == 0 else "degraded",
        },
        {
            "service": "microsoft_signin",
            "status": "healthy" if bool(auth_snapshot["microsoft"]["healthy"]) else "degraded",
        },
        {
            "service": "telnyx_readiness",
            "status": "healthy" if telnyx_ready else "degraded",
        },
        {"service": "database", "status": "healthy" if db_ok else "degraded"},
        {"service": "redis", "status": redis_state},
    ]

    degraded_services = [
        s["service"]
        for s in services
        if s["status"] in {"degraded", "unreachable", "down", "red"}
    ]

    overall_status = "healthy"
    if release_blockers:
        overall_status = "blocked"
    elif degraded_services:
        overall_status = "degraded"

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_status": overall_status,
        "services": services,
        "degraded_services": degraded_services,
        "active_incidents": active_incidents,
        "auth": auth_snapshot,

        "nemsis": {
            "active_version": "3.5.0",
            "local_schematron_configured": bool(str(settings.nemsis_local_schematron_dir or "").strip()),
            "cta_endpoint_ready": bool(str(settings.nemsis_cta_endpoint or "").strip()),
            "national_endpoint_ready": bool(str(settings.nemsis_national_endpoint or "").strip()),
            "validation_status": nemsis_report.get("status", "not_available"),
            "certification_status": nemsis_report.get("certification_status"),
        },
        "neris": {
            "validation_status": neris_report.get("status", "not_available"),
            "certification_status": neris_report.get("certification_status"),
        },
        "telnyx": {
            "number": telnyx_central_number,
            "configured_number": configured_number,
            "voice_binding": configured_number == telnyx_central_number,
            "messaging_profile": bool(str(settings.telnyx_messaging_profile_id or "").strip()),
            "webhook_health": bool(str(settings.telnyx_api_key or "").strip()),
            "stale_binding_detected": configured_number not in {"", telnyx_central_number},
            "healthy": telnyx_ready,
            "blockers": telnyx_blockers,
        },
        "release": release,
        "release_blockers": release_blockers,
        "integration_state": integration_state,
    }


@router.get("/release-readiness")
def release_readiness_gate(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> dict:
    """
    Comprehensive release readiness gate.
    Checks database health, migration state, integration configs,
    known placeholders, and critical service availability.
    Returns structured pass/fail gate report.
    """
    import importlib

    from sqlalchemy import text as sa_text

    gates: list[dict[str, object]] = []

    # Gate 1: Database connectivity
    try:
        db.execute(sa_text("SELECT 1"))
        gates.append(_GateCheck("database_connectivity", True, "PostgreSQL reachable").to_dict())
    except Exception as exc:
        gates.append(_GateCheck("database_connectivity", False, str(exc)).to_dict())

    # Gate 2: Alembic migration head check
    try:
        result = db.execute(sa_text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = result.fetchone()
        current_rev = row[0] if row else "none"
        gates.append(_GateCheck(
            "migration_current", True, f"alembic_head={current_rev}",
        ).to_dict())
    except Exception as exc:
        gates.append(_GateCheck("migration_current", False, str(exc)).to_dict())

    # Gate 3: Critical tables exist
    critical_tables = [
        "tenants", "users", "billing_cases", "edi_artifacts",
        "epcr_charts", "cad_incidents", "fleet_units",
    ]
    missing_tables: list[str] = []
    for tbl in critical_tables:
        try:
            db.execute(sa_text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"), {"t": tbl})  # noqa: S608
            row = db.execute(sa_text("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = :t)"), {"t": tbl}).scalar()  # noqa: S608
            if not row:
                missing_tables.append(tbl)
        except Exception:
            missing_tables.append(tbl)
    gates.append(_GateCheck(
        "critical_tables",
        len(missing_tables) == 0,
        f"missing={missing_tables}" if missing_tables else "all_present",
    ).to_dict())

    auth_snapshot, auth_blockers = _auth_health_snapshot()
    release = _release_metadata()

    # Gate 4: Office Ally SFTP configured
    settings = get_settings()
    oa_host = str(settings.officeally_sftp_host or "")
    gates.append(_GateCheck(
        "officeally_sftp_configured",
        bool(oa_host),
        f"host={'set' if oa_host else 'missing'}",
    ).to_dict())

    # Gate 5: Stripe configured
    stripe_state = settings.integration_state_table().get("stripe", {})
    stripe_placeholder_fields = stripe_state.get("placeholder_fields", [])
    gates.append(_GateCheck(
        "stripe_configured",
        bool(stripe_state.get("configured")),
        (
            f"placeholder_fields={','.join(stripe_placeholder_fields)}"
            if isinstance(stripe_placeholder_fields, list) and stripe_placeholder_fields
            else "key_present"
            if str(settings.stripe_secret_key or "")
            else "key_missing"
        ),
    ).to_dict())

    # Gate 6: Telnyx configured
    telnyx_key = str(settings.telnyx_api_key or "")
    gates.append(_GateCheck(
        "telnyx_configured",
        bool(telnyx_key),
        "key_present" if telnyx_key else "key_missing",
    ).to_dict())

    # Gate 7: AWS region set
    aws_region = os.environ.get("AWS_DEFAULT_REGION") or os.environ.get("AWS_REGION", "")
    gates.append(_GateCheck(
        "aws_region_configured",
        bool(aws_region),
        f"region={aws_region or 'unset'}",
    ).to_dict())

    # Gate 8: Redis connectivity
    try:
        redis_mod = importlib.import_module("redis")
        redis_url = str(settings.redis_url or "")
        if redis_url:
            r = redis_mod.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            gates.append(_GateCheck("redis_connectivity", True, "reachable").to_dict())
        else:
            gates.append(_GateCheck("redis_connectivity", False, "REDIS_URL not set").to_dict())
    except Exception as exc:
        gates.append(_GateCheck("redis_connectivity", False, str(exc)).to_dict())

    # Gate 9: No known placeholder tenants
    try:
        count = db.execute(
            sa_text("SELECT count(*) FROM tenants WHERE name ILIKE '%placeholder%' OR name ILIKE '%demo%' OR name ILIKE '%test%'")
        ).scalar() or 0
        gates.append(_GateCheck(
            "no_placeholder_tenants",
            int(count) == 0,
            f"found={count}" if count else "clean",
        ).to_dict())
    except Exception:
        gates.append(_GateCheck("no_placeholder_tenants", True, "table_not_checked").to_dict())

    # Gate 10: Browser auth mode is FusionEMS JWT
    auth_mode = str(settings.auth_mode or "").strip().lower()
    gates.append(_GateCheck(
        "browser_auth_mode_fusion_jwt",
        auth_mode == "fusion_jwt",
        f"mode={auth_mode or 'unset'}",
    ).to_dict())

    # Gate 11: Microsoft Entra sign-in config valid and non-placeholder
    microsoft_healthy = bool(auth_snapshot["microsoft"]["healthy"])
    gates.append(_GateCheck(
        "microsoft_auth_config_valid",
        microsoft_healthy,
        "valid" if microsoft_healthy else "; ".join(auth_blockers) or "invalid",
    ).to_dict())

    # Gate 12: Microsoft tenant identifier valid format
    tenant_value = str(settings.graph_tenant_id or "")
    tenant_valid = is_valid_entra_tenant_identifier(tenant_value)
    gates.append(_GateCheck(
        "microsoft_tenant_identifier_valid",
        tenant_valid,
        "uuid_or_domain" if tenant_valid else "invalid_or_placeholder",
    ).to_dict())

    # Gate 13: Release metadata visible
    release_version = str(release.get("version") or "")
    gates.append(_GateCheck(
        "release_metadata_visible",
        bool(release_version) and release_version != "unknown",
        f"version={release_version or 'unknown'}",
    ).to_dict())

    # Gate 14: Rollback readiness signal present
    rollback_ready = bool(release.get("rollback_ready"))
    gates.append(_GateCheck(
        "rollback_readiness",
        rollback_ready,
        "ready" if rollback_ready else "not_ready",
    ).to_dict())

    passed = sum(1 for g in gates if g["passed"])
    total = len(gates)
    all_passed = passed == total

    return {
        "ready": all_passed,
        "score": f"{passed}/{total}",
        "passed_count": passed,
        "total_count": total,
        "verdict": "RELEASE_READY" if all_passed else "BLOCKED",
        "gates": gates,
    }
