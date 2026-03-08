# pylint: disable=unused-argument

"""
Platform Core API Router — Tenant lifecycle, user provisioning, implementation,
feature flags, release/environment, system configuration, founder command center.

All endpoints use RBAC (require_role), tenant scoping, structured error responses.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    require_role,
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
