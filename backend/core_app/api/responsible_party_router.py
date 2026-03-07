"""Responsible Party API — guarantor CRUD, patient links, insurance."""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.responsible_party import (
    InsuranceSubscriberCreate,
    InsuranceSubscriberListResponse,
    InsuranceSubscriberResponse,
    PatientResponsiblePartyLinkCreate,
    PatientResponsiblePartyLinkListResponse,
    PatientResponsiblePartyLinkResponse,
    ResponsibilityStateUpdate,
    ResponsiblePartyCreate,
    ResponsiblePartyListResponse,
    ResponsiblePartyResponse,
    ResponsiblePartyUpdate,
)
from core_app.services.responsible_party_service import (
    ResponsiblePartyService,
)

router = APIRouter(
    prefix="/api/v1/responsible-parties",
    tags=["responsible-parties"],
)


def _svc(
    db: AsyncSession = Depends(get_async_db_session),
) -> ResponsiblePartyService:
    return ResponsiblePartyService(db=db)


# ── RESPONSIBLE PARTY CRUD ────────────────────────────────────────────────

@router.post(
    "",
    response_model=ResponsiblePartyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_responsible_party(
    payload: ResponsiblePartyCreate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> ResponsiblePartyResponse:
    return await svc.create_responsible_party(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("", response_model=ResponsiblePartyListResponse)
async def list_responsible_parties(
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> ResponsiblePartyListResponse:
    return await svc.list_responsible_parties(
        tenant_id=current_user.tenant_id
    )


@router.get("/{party_id}", response_model=ResponsiblePartyResponse)
async def get_responsible_party(
    party_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> ResponsiblePartyResponse:
    return await svc.get_responsible_party(
        tenant_id=current_user.tenant_id, party_id=party_id
    )


@router.patch("/{party_id}", response_model=ResponsiblePartyResponse)
async def update_responsible_party(
    party_id: uuid.UUID,
    payload: ResponsiblePartyUpdate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> ResponsiblePartyResponse:
    return await svc.update_responsible_party(
        tenant_id=current_user.tenant_id,
        party_id=party_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


# ── INSURANCE SUBSCRIBER PROFILES ────────────────────────────────────────

@router.post(
    "/{party_id}/insurance",
    response_model=InsuranceSubscriberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subscriber_profile(
    party_id: uuid.UUID,
    payload: InsuranceSubscriberCreate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> InsuranceSubscriberResponse:
    return await svc.create_subscriber_profile(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get(
    "/{party_id}/insurance",
    response_model=InsuranceSubscriberListResponse,
)
async def list_subscriber_profiles(
    party_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> InsuranceSubscriberListResponse:
    return await svc.list_subscriber_profiles(
        tenant_id=current_user.tenant_id, party_id=party_id
    )


# ── PATIENT LINKS ────────────────────────────────────────────────────────

link_router = APIRouter(
    prefix="/api/v1/patients/{patient_id}/responsible-parties",
    tags=["responsible-parties"],
)


@link_router.post(
    "",
    response_model=PatientResponsiblePartyLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_to_patient(
    patient_id: uuid.UUID,
    payload: PatientResponsiblePartyLinkCreate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> PatientResponsiblePartyLinkResponse:
    return await svc.link_to_patient(
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@link_router.get(
    "",
    response_model=PatientResponsiblePartyLinkListResponse,
)
async def list_patient_links(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> PatientResponsiblePartyLinkListResponse:
    return await svc.list_patient_links(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


@link_router.post(
    "/{link_id}/state",
    response_model=PatientResponsiblePartyLinkResponse,
)
async def update_responsibility_state(
    patient_id: uuid.UUID,
    link_id: uuid.UUID,
    payload: ResponsibilityStateUpdate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("billing", "admin", "founder")
    ),
    svc: ResponsiblePartyService = Depends(_svc),
) -> PatientResponsiblePartyLinkResponse:
    return await svc.update_responsibility_state(
        tenant_id=current_user.tenant_id,
        link_id=link_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )
