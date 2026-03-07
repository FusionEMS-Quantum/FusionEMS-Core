"""Contact Preference API — preferences, opt-out, language."""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.contact_preference import (
    ContactPreferenceResponse,
    ContactPreferenceUpsert,
    LanguagePreferenceResponse,
    LanguagePreferenceUpsert,
    OptOutEventCreate,
    OptOutEventListResponse,
    OptOutEventResponse,
)
from core_app.services.contact_preference_service import (
    ContactPreferenceService,
)

router = APIRouter(
    prefix="/api/v1/patients/{patient_id}/contact-preferences",
    tags=["contact-preferences"],
)


def _svc(
    db: AsyncSession = Depends(get_async_db_session),
) -> ContactPreferenceService:
    return ContactPreferenceService(db=db)


# ── CONTACT PREFERENCES ──────────────────────────────────────────────────

@router.put("", response_model=ContactPreferenceResponse)
async def upsert_preference(
    patient_id: uuid.UUID,
    payload: ContactPreferenceUpsert,
    request: Request,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ContactPreferenceService = Depends(_svc),
) -> ContactPreferenceResponse:
    return await svc.upsert_preference(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
        correlation_id=request.state.correlation_id,
    )


@router.get("", response_model=ContactPreferenceResponse | None)
async def get_preference(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ContactPreferenceService = Depends(_svc),
) -> ContactPreferenceResponse | None:
    return await svc.get_patient_preference(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


# ── OPT-OUT ──────────────────────────────────────────────────────────────

@router.post(
    "/opt-out",
    response_model=OptOutEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_opt_out(
    patient_id: uuid.UUID,
    payload: OptOutEventCreate,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ContactPreferenceService = Depends(_svc),
) -> OptOutEventResponse:
    return await svc.record_opt_out(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


@router.get("/opt-out", response_model=OptOutEventListResponse)
async def list_opt_out_events(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ContactPreferenceService = Depends(_svc),
) -> OptOutEventListResponse:
    return await svc.list_opt_out_events(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


# ── LANGUAGE ──────────────────────────────────────────────────────────────

@router.put("/language", response_model=LanguagePreferenceResponse)
async def upsert_language(
    patient_id: uuid.UUID,
    payload: LanguagePreferenceUpsert,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ContactPreferenceService = Depends(_svc),
) -> LanguagePreferenceResponse:
    return await svc.upsert_language_preference(
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


@router.get("/language", response_model=LanguagePreferenceResponse | None)
async def get_language(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: ContactPreferenceService = Depends(_svc),
) -> LanguagePreferenceResponse | None:
    return await svc.get_language_preference(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )
