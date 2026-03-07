"""AI Platform Router — Registry, Orchestration, Governance, Override, Command Center."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_role,
)
from core_app.schemas.ai_platform import (
    AICommandCenterMetrics,
    AIHumanOverrideRequest,
    AIReviewActionRequest,
    AIReviewItemResponse,
    AIUseCaseCreate,
    AIUseCaseResponse,
    AIUseCaseUpdate,
    AIWorkflowRunResponse,
    AIWorkflowStartRequest,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.ai_platform.command_center_service import AICommandCenterService
from core_app.services.ai_platform.governance_service import AIGovernanceService
from core_app.services.ai_platform.orchestration_service import AIOrchestrationService
from core_app.services.ai_platform.override_service import AIOverrideService
from core_app.services.ai_platform.registry_service import AIRegistryService

router = APIRouter(prefix="/api/v1/ai-platform", tags=["ai-platform"])


# ── USE-CASE REGISTRY ────────────────────────────────────────────────────────


@router.get("/registry/use-cases", response_model=list[AIUseCaseResponse])
def list_use_cases(
    domain: str | None = Query(None),
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(get_current_user),
) -> list:
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
) -> list:
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


# ── FOUNDER COMMAND CENTER ────────────────────────────────────────────────────


@router.get("/command-center/metrics", response_model=AICommandCenterMetrics)
def get_command_center_metrics(
    db: Session = Depends(db_session_dependency),
    user: CurrentUser = Depends(require_role("founder", "agency_admin")),
) -> AICommandCenterMetrics:
    svc = AICommandCenterService(db, user)
    return svc.get_metrics()
