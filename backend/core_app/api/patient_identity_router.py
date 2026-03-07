"""Patient Identity API — aliases, identifiers, duplicates, merges, flags."""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.patient_identity import (
    DuplicateCandidateListResponse,
    DuplicateCandidateResponse,
    DuplicateResolutionUpdate,
    MergeRequestCreate,
    MergeRequestListResponse,
    MergeRequestResponse,
    MergeRequestReview,
    PatientAliasCreate,
    PatientAliasListResponse,
    PatientAliasResponse,
    PatientIdentifierCreate,
    PatientIdentifierListResponse,
    PatientIdentifierResponse,
    RelationshipFlagCreate,
    RelationshipFlagListResponse,
    RelationshipFlagResolve,
    RelationshipFlagResponse,
)
from core_app.services.patient_identity_service import PatientIdentityService

router = APIRouter(
    prefix="/api/v1/patients/{patient_id}/identity",
    tags=["patient-identity"],
)


def _svc(
    db: AsyncSession = Depends(get_async_db_session),
) -> PatientIdentityService:
    return PatientIdentityService(db=db)


# ── ALIASES ───────────────────────────────────────────────────────────────

@router.post(
    "/aliases",
    response_model=PatientAliasResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_alias(
    patient_id: uuid.UUID,
    payload: PatientAliasCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> PatientAliasResponse:
    return await svc.create_alias(
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("/aliases", response_model=PatientAliasListResponse)
async def list_aliases(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: PatientIdentityService = Depends(_svc),
) -> PatientAliasListResponse:
    return await svc.list_aliases(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


# ── IDENTIFIERS ───────────────────────────────────────────────────────────

@router.post(
    "/identifiers",
    response_model=PatientIdentifierResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_identifier(
    patient_id: uuid.UUID,
    payload: PatientIdentifierCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> PatientIdentifierResponse:
    return await svc.create_identifier(
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("/identifiers", response_model=PatientIdentifierListResponse)
async def list_identifiers(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: PatientIdentityService = Depends(_svc),
) -> PatientIdentifierListResponse:
    return await svc.list_identifiers(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


# ── RELATIONSHIP FLAGS ────────────────────────────────────────────────────

@router.post(
    "/flags",
    response_model=RelationshipFlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_flag(
    patient_id: uuid.UUID,
    payload: RelationshipFlagCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_role("ems", "admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> RelationshipFlagResponse:
    return await svc.create_flag(
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("/flags", response_model=RelationshipFlagListResponse)
async def list_flags(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: PatientIdentityService = Depends(_svc),
) -> RelationshipFlagListResponse:
    return await svc.list_flags(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


@router.post("/flags/{flag_id}/resolve", response_model=RelationshipFlagResponse)
async def resolve_flag(
    patient_id: uuid.UUID,
    flag_id: uuid.UUID,
    payload: RelationshipFlagResolve,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> RelationshipFlagResponse:
    return await svc.resolve_flag(
        tenant_id=current_user.tenant_id,
        flag_id=flag_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


# ── DUPLICATES (tenant-level, not patient-nested) ────────────────────────

dup_router = APIRouter(
    prefix="/api/v1/identity/duplicates",
    tags=["patient-identity"],
)


@dup_router.get("", response_model=DuplicateCandidateListResponse)
async def list_duplicate_candidates(
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: PatientIdentityService = Depends(_svc),
) -> DuplicateCandidateListResponse:
    return await svc.list_duplicate_candidates(
        tenant_id=current_user.tenant_id
    )


@dup_router.post(
    "/{candidate_id}/resolve",
    response_model=DuplicateCandidateResponse,
)
async def resolve_duplicate(
    candidate_id: uuid.UUID,
    payload: DuplicateResolutionUpdate,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> DuplicateCandidateResponse:
    return await svc.resolve_duplicate(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


# ── MERGE REQUESTS (tenant-level) ────────────────────────────────────────

merge_router = APIRouter(
    prefix="/api/v1/identity/merges",
    tags=["patient-identity"],
)


@merge_router.post(
    "",
    response_model=MergeRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_merge_request(
    payload: MergeRequestCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> MergeRequestResponse:
    return await svc.create_merge_request(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@merge_router.get("", response_model=MergeRequestListResponse)
async def list_merge_requests(
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> MergeRequestListResponse:
    return await svc.list_merge_requests(
        tenant_id=current_user.tenant_id
    )


@merge_router.post(
    "/{merge_request_id}/review",
    response_model=MergeRequestResponse,
)
async def review_merge_request(
    merge_request_id: uuid.UUID,
    payload: MergeRequestReview,
    request: Request,
    current_user: CurrentUser = Depends(require_role("admin", "founder")),
    svc: PatientIdentityService = Depends(_svc),
) -> MergeRequestResponse:
    return await svc.review_merge_request(
        tenant_id=current_user.tenant_id,
        merge_request_id=merge_request_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )
