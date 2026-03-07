"""Facility API — CRUD, contacts, notes, service profiles, friction flags."""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.facility import (
    FacilityContactCreate,
    FacilityContactListResponse,
    FacilityContactResponse,
    FacilityCreate,
    FacilityFrictionFlagCreate,
    FacilityFrictionFlagListResponse,
    FacilityFrictionFlagResponse,
    FacilityListResponse,
    FacilityRelationshipNoteCreate,
    FacilityRelationshipNoteListResponse,
    FacilityRelationshipNoteResponse,
    FacilityResponse,
    FacilityServiceProfileCreate,
    FacilityServiceProfileListResponse,
    FacilityServiceProfileResponse,
    FacilityUpdate,
    FrictionFlagResolve,
)
from core_app.services.facility_service import FacilityService

router = APIRouter(
    prefix="/api/v1/facilities",
    tags=["facilities"],
)


def _svc(
    db: AsyncSession = Depends(get_async_db_session),
) -> FacilityService:
    return FacilityService(db=db)


# ── FACILITY CRUD ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=FacilityResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_facility(
    payload: FacilityCreate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityResponse:
    return await svc.create_facility(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("", response_model=FacilityListResponse)
async def list_facilities(
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityListResponse:
    return await svc.list_facilities(
        tenant_id=current_user.tenant_id
    )


@router.get("/{facility_id}", response_model=FacilityResponse)
async def get_facility(
    facility_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityResponse:
    return await svc.get_facility(
        tenant_id=current_user.tenant_id, facility_id=facility_id
    )


@router.patch("/{facility_id}", response_model=FacilityResponse)
async def update_facility(
    facility_id: uuid.UUID,
    payload: FacilityUpdate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityResponse:
    return await svc.update_facility(
        tenant_id=current_user.tenant_id,
        facility_id=facility_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


# ── CONTACTS ──────────────────────────────────────────────────────────────

@router.post(
    "/{facility_id}/contacts",
    response_model=FacilityContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_contact(
    facility_id: uuid.UUID,
    payload: FacilityContactCreate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityContactResponse:
    return await svc.add_contact(
        tenant_id=current_user.tenant_id,
        facility_id=facility_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get(
    "/{facility_id}/contacts",
    response_model=FacilityContactListResponse,
)
async def list_contacts(
    facility_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityContactListResponse:
    return await svc.list_contacts(
        tenant_id=current_user.tenant_id, facility_id=facility_id
    )


# ── NOTES ─────────────────────────────────────────────────────────────────

@router.post(
    "/{facility_id}/notes",
    response_model=FacilityRelationshipNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_note(
    facility_id: uuid.UUID,
    payload: FacilityRelationshipNoteCreate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("ems", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityRelationshipNoteResponse:
    return await svc.add_note(
        tenant_id=current_user.tenant_id,
        facility_id=facility_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get(
    "/{facility_id}/notes",
    response_model=FacilityRelationshipNoteListResponse,
)
async def list_notes(
    facility_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityRelationshipNoteListResponse:
    return await svc.list_notes(
        tenant_id=current_user.tenant_id, facility_id=facility_id
    )


# ── SERVICE PROFILES ──────────────────────────────────────────────────────

@router.post(
    "/{facility_id}/services",
    response_model=FacilityServiceProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_service_profile(
    facility_id: uuid.UUID,
    payload: FacilityServiceProfileCreate,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityServiceProfileResponse:
    return await svc.add_service_profile(
        tenant_id=current_user.tenant_id,
        facility_id=facility_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


@router.get(
    "/{facility_id}/services",
    response_model=FacilityServiceProfileListResponse,
)
async def list_service_profiles(
    facility_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityServiceProfileListResponse:
    return await svc.list_service_profiles(
        tenant_id=current_user.tenant_id, facility_id=facility_id
    )


# ── FRICTION FLAGS ────────────────────────────────────────────────────────

@router.post(
    "/{facility_id}/friction",
    response_model=FacilityFrictionFlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_friction_flag(
    facility_id: uuid.UUID,
    payload: FacilityFrictionFlagCreate,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("ems", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityFrictionFlagResponse:
    return await svc.add_friction_flag(
        tenant_id=current_user.tenant_id,
        facility_id=facility_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get(
    "/{facility_id}/friction",
    response_model=FacilityFrictionFlagListResponse,
)
async def list_friction_flags(
    facility_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityFrictionFlagListResponse:
    return await svc.list_friction_flags(
        tenant_id=current_user.tenant_id, facility_id=facility_id
    )


@router.post(
    "/{facility_id}/friction/{flag_id}/resolve",
    response_model=FacilityFrictionFlagResponse,
)
async def resolve_friction_flag(
    facility_id: uuid.UUID,
    flag_id: uuid.UUID,
    payload: FrictionFlagResolve,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: FacilityService = Depends(_svc),
) -> FacilityFrictionFlagResponse:
    return await svc.resolve_friction_flag(
        tenant_id=current_user.tenant_id,
        flag_id=flag_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )
