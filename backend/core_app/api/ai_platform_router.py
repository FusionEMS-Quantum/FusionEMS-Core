"""AI Platform Router — Registry, Orchestration, Governance, Override, Command Center."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_role,
)
from core_app.schemas.ai_platform import (
    AICommandCenterMetrics,
    AIDomainCopilotResponse,
    AIExplanationResponse,
    AIGuardrailRuleResponse,
    AIHumanOverrideRequest,
    AIInferenceResultRequest,
    AIPromptTemplateCreate,
    AIPromptTemplateResponse,
    AIPromptTemplateUpdate,
    AIProtectedActionResponse,
    AIReviewActionRequest,
    AIReviewItemResponse,
    AITenantSettingsResponse,
    AITenantSettingsUpdate,
    AIUseCaseCreate,
    AIUseCaseResponse,
    AIUseCaseUpdate,
    AIUserFacingSummaryCreate,
    AIUserFacingSummaryResponse,
    AIWorkflowRunResponse,
    AIWorkflowStartRequest,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.ai_platform.command_center_service import AICommandCenterService
from core_app.services.ai_platform.governance_service import AIGovernanceService
from core_app.services.ai_platform.orchestration_service import AIOrchestrationService
from core_app.services.ai_platform.override_service import AIOverrideService
from core_app.services.ai_platform.registry_service import AIRegistryService
from core_app.services.ai_platform.seed_service import AISeedService

router = APIRouter(prefix="/api/v1/ai-platform", tags=["ai-platform"])


# ── USE-CASE REGISTRY ────────────────────────────────────────────────────────


@router.get("/registry/use-cases", response_model=list[AIUseCaseResponse])
def list_use_cases(
    domain: str | None = Query(None),
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> list[AIUseCaseResponse]:
    svc = AIRegistryService(db, user)
    return svc.list_use_cases(domain=domain)


@router.get("/registry/use-cases/{use_case_id}", response_model=AIUseCaseResponse)
def get_use_case(
    use_case_id: uuid.UUID,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> AIUseCaseResponse:
    svc = AIRegistryService(db, user)
    return svc.get_use_case(use_case_id)


@router.post("/registry/use-cases", response_model=AIUseCaseResponse, status_code=201)
def create_use_case(
    payload: AIUseCaseCreate,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIUseCaseResponse:
    svc = AIRegistryService(db, user)
    return svc.create_use_case(payload)


@router.patch("/registry/use-cases/{use_case_id}", response_model=AIUseCaseResponse)
def update_use_case(
    use_case_id: uuid.UUID,
    payload: AIUseCaseUpdate,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIUseCaseResponse:
    svc = AIRegistryService(db, user)
    return svc.update_use_case(use_case_id, payload)


@router.post("/registry/use-cases/{use_case_id}/disable", response_model=AIUseCaseResponse)
def disable_use_case(
    use_case_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIUseCaseResponse:
    svc = AIRegistryService(db, user)
    return svc.disable_use_case(use_case_id, reason=payload.get("reason", "Disabled by admin"))


# ── WORKFLOW ORCHESTRATION ────────────────────────────────────────────────────


@router.post("/workflows", response_model=AIWorkflowRunResponse, status_code=201)
def start_workflow(
    payload: AIWorkflowStartRequest,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> AIWorkflowRunResponse:
    svc = AIOrchestrationService(db, user)
    return svc.start_workflow(
        use_case_id=payload.use_case_id,
        correlation_id=payload.correlation_id,
        context=payload.context_snapshot,
    )


@router.get("/workflows/{workflow_id}", response_model=AIWorkflowRunResponse)
def get_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> AIWorkflowRunResponse:
    svc = AIOrchestrationService(db, user)
    return svc.get_workflow(workflow_id)


@router.post("/workflows/{workflow_id}/result", response_model=AIWorkflowRunResponse)
def submit_inference_result(
    workflow_id: uuid.UUID,
    payload: AIInferenceResultRequest,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> AIWorkflowRunResponse:
    svc = AIOrchestrationService(db, user)
    return svc.record_result(
        workflow_id=workflow_id,
        provider_response=payload.provider_response,
        explanation=payload.explanation,
    )


# ── EXPLAINABILITY ────────────────────────────────────────────────────────


@router.get("/explainability/{workflow_id}", response_model=list[AIExplanationResponse])
def get_explanations(
    workflow_id: uuid.UUID,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> list[AIExplanationResponse]:
    svc = AIOrchestrationService(db, user)
    return svc.get_explanations(workflow_id)


# ── HUMAN OVERRIDE ────────────────────────────────────────────────────────────


@router.post("/workflows/{workflow_id}/override", response_model=AIWorkflowRunResponse)
def override_workflow(
    workflow_id: uuid.UUID,
    payload: AIHumanOverrideRequest,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIWorkflowRunResponse:
    svc = AIOverrideService(db, user)
    return svc.override_workflow(workflow_id, payload.new_state, payload.reason)


@router.post("/workflows/{workflow_id}/resume", response_model=AIWorkflowRunResponse)
def resume_ai(
    workflow_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIWorkflowRunResponse:
    svc = AIOverrideService(db, user)
    return svc.resume_ai(workflow_id, reason=payload.get("reason", "Resumed by admin"))


# ── REVIEW QUEUE ──────────────────────────────────────────────────────────────


@router.get("/reviews", response_model=list[AIReviewItemResponse])
def list_reviews(
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> list[AIReviewItemResponse]:
    svc = AIOverrideService(db, user)
    return svc.list_review_queue()


@router.post("/reviews/{review_id}/approve", response_model=AIReviewItemResponse)
def approve_review(
    review_id: uuid.UUID,
    payload: AIReviewActionRequest,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIReviewItemResponse:
    svc = AIOverrideService(db, user)
    return svc.approve_review(review_id, notes=payload.reason)


@router.post("/reviews/{review_id}/reject", response_model=AIReviewItemResponse)
def reject_review(
    review_id: uuid.UUID,
    payload: AIReviewActionRequest,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIReviewItemResponse:
    svc = AIOverrideService(db, user)
    return svc.reject_review(
        review_id,
        reason=payload.reason or "Rejected",
        regenerate_requested=payload.regenerate_requested,
    )


# ── GOVERNANCE ────────────────────────────────────────────────────────────────


@router.get("/governance/guardrails", response_model=list[AIGuardrailRuleResponse])
def list_guardrail_rules(
    domain: str | None = Query(None),
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> list[AIGuardrailRuleResponse]:
    svc = AIGovernanceService(db, user)
    return svc.list_guardrail_rules(domain=domain)


@router.get("/governance/protected-actions", response_model=list[AIProtectedActionResponse])
def list_protected_actions(
    domain: str | None = Query(None),
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> list[AIProtectedActionResponse]:
    svc = AIGovernanceService(db, user)
    return svc.list_protected_actions(domain=domain)


# ── PROMPT TEMPLATES ────────────────────────────────────────────────────────


@router.get("/prompt-templates", response_model=list[AIPromptTemplateResponse])
def list_prompt_templates(
    domain: str | None = Query(None),
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> list[AIPromptTemplateResponse]:
    svc = AIRegistryService(db, user)
    return svc.list_prompt_templates(domain=domain)


@router.post("/prompt-templates", response_model=AIPromptTemplateResponse, status_code=201)
def create_prompt_template(
    payload: AIPromptTemplateCreate,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIPromptTemplateResponse:
    svc = AIRegistryService(db, user)
    return svc.create_prompt_template(payload)


@router.patch("/prompt-templates/{template_id}", response_model=AIPromptTemplateResponse)
def update_prompt_template(
    template_id: uuid.UUID,
    payload: AIPromptTemplateUpdate,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AIPromptTemplateResponse:
    svc = AIRegistryService(db, user)
    return svc.update_prompt_template(template_id, payload)


# ── DOMAIN COPILOTS ───────────────────────────────────────────────────────────


@router.get("/copilots", response_model=list[AIDomainCopilotResponse])
def list_copilots(
    domain: str | None = Query(None),
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> list[AIDomainCopilotResponse]:
    svc = AIRegistryService(db, user)
    return svc.list_copilots(domain=domain)


# ── FOUNDER COMMAND CENTER ────────────────────────────────────────────────────


@router.get("/command-center/metrics", response_model=AICommandCenterMetrics)
def get_command_center_metrics(
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AICommandCenterMetrics:
    svc = AICommandCenterService(db, user)
    return svc.get_metrics()


# ── TENANT AI SETTINGS ────────────────────────────────────────────────────────


@router.get("/settings", response_model=AITenantSettingsResponse)
def get_tenant_settings(
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AITenantSettingsResponse:
    svc = AICommandCenterService(db, user)
    settings = svc.get_tenant_settings()
    if not settings:
        # Auto-create defaults on first access
        seed = AISeedService(db, str(user.tenant_id))
        settings = seed.ensure_tenant_settings()
    return settings


@router.patch("/settings", response_model=AITenantSettingsResponse)
def update_tenant_settings(
    payload: AITenantSettingsUpdate,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AITenantSettingsResponse:
    svc = AICommandCenterService(db, user)
    return svc.update_tenant_settings(payload)


# ── USER-FACING SUMMARY (Simple Mode) ────────────────────────────────────────


@router.post(
    "/workflows/{workflow_id}/summary",
    response_model=AIUserFacingSummaryResponse,
    status_code=201,
)
def create_user_facing_summary(
    workflow_id: uuid.UUID,
    payload: AIUserFacingSummaryCreate,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> AIUserFacingSummaryResponse:
    svc = AICommandCenterService(db, user)
    return svc.create_user_facing_summary(workflow_id, payload)


@router.get(
    "/workflows/{workflow_id}/summary",
    response_model=AIUserFacingSummaryResponse,
)
def get_user_facing_summary(
    workflow_id: uuid.UUID,
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> AIUserFacingSummaryResponse:
    svc = AICommandCenterService(db, user)
    summary = svc.get_user_facing_summary(workflow_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No user-facing summary found for this workflow.")
    return summary


# ── SEED DOMAIN COPILOTS ─────────────────────────────────────────────────────


@router.post("/seed", status_code=200)
def seed_ai_platform(
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder")),
) -> dict:
    svc = AISeedService(db, str(user.tenant_id))
    return svc.seed_all()
