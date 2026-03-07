"""Relationship History API — timelines, notes, warnings, summaries."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.relationship_history import (
    FacilityWarningFlagCreate,
    FacilityWarningFlagListResponse,
    FacilityWarningFlagResponse,
    InternalAccountNoteCreate,
    InternalAccountNoteListResponse,
    InternalAccountNoteResponse,
    PatientWarningFlagCreate,
    PatientWarningFlagListResponse,
    PatientWarningFlagResponse,
    RelationshipSummaryListResponse,
    TimelineEventCreate,
    TimelineEventListResponse,
    TimelineEventResponse,
    WarningFlagResolve,
)
from core_app.services.relationship_history_service import (
    RelationshipHistoryService,
)

# ── PATIENT-SCOPED ────────────────────────────────────────────────────────

patient_router = APIRouter(
    prefix="/api/v1/patients/{patient_id}/history",
    tags=["relationship-history"],
)


def _svc(
    db: AsyncSession = Depends(get_async_db_session),
) -> RelationshipHistoryService:
    return RelationshipHistoryService(db=db)


@patient_router.get("/timeline", response_model=TimelineEventListResponse)
async def patient_timeline(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> TimelineEventListResponse:
    return await svc.list_patient_timeline(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


@patient_router.get("/notes", response_model=InternalAccountNoteListResponse)
async def patient_notes(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> InternalAccountNoteListResponse:
    return await svc.list_patient_notes(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


@patient_router.get("/warnings", response_model=PatientWarningFlagListResponse)
async def patient_warnings(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> PatientWarningFlagListResponse:
    return await svc.list_patient_warnings(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


@patient_router.post(
    "/warnings",
    response_model=PatientWarningFlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_patient_warning(
    patient_id: uuid.UUID,
    payload: PatientWarningFlagCreate,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> PatientWarningFlagResponse:
    return await svc.create_patient_warning(
        tenant_id=current_user.tenant_id,
        patient_id=patient_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


@patient_router.post(
    "/warnings/{flag_id}/resolve",
    response_model=PatientWarningFlagResponse,
)
async def resolve_patient_warning(
    patient_id: uuid.UUID,
    flag_id: uuid.UUID,
    payload: WarningFlagResolve,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> PatientWarningFlagResponse:
    return await svc.resolve_patient_warning(
        tenant_id=current_user.tenant_id,
        flag_id=flag_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


@patient_router.get("/summaries", response_model=RelationshipSummaryListResponse)
async def patient_summaries(
    patient_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> RelationshipSummaryListResponse:
    return await svc.list_patient_summaries(
        tenant_id=current_user.tenant_id, patient_id=patient_id
    )


# ── FACILITY-SCOPED ──────────────────────────────────────────────────────

facility_router = APIRouter(
    prefix="/api/v1/facilities/{facility_id}/history",
    tags=["relationship-history"],
)


@facility_router.get("/timeline", response_model=TimelineEventListResponse)
async def facility_timeline(
    facility_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> TimelineEventListResponse:
    return await svc.list_facility_timeline(
        tenant_id=current_user.tenant_id, facility_id=facility_id
    )


@facility_router.get(
    "/warnings",
    response_model=FacilityWarningFlagListResponse,
)
async def facility_warnings(
    facility_id: uuid.UUID,
    current_user: CurrentUser = Depends(
        require_role("ems", "billing", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> FacilityWarningFlagListResponse:
    return await svc.list_facility_warnings(
        tenant_id=current_user.tenant_id, facility_id=facility_id
    )


@facility_router.post(
    "/warnings",
    response_model=FacilityWarningFlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_facility_warning(
    facility_id: uuid.UUID,
    payload: FacilityWarningFlagCreate,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> FacilityWarningFlagResponse:
    return await svc.create_facility_warning(
        tenant_id=current_user.tenant_id,
        facility_id=facility_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


@facility_router.post(
    "/warnings/{flag_id}/resolve",
    response_model=FacilityWarningFlagResponse,
)
async def resolve_facility_warning(
    facility_id: uuid.UUID,
    flag_id: uuid.UUID,
    payload: WarningFlagResolve,
    current_user: CurrentUser = Depends(
        require_role("admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> FacilityWarningFlagResponse:
    return await svc.resolve_facility_warning(
        tenant_id=current_user.tenant_id,
        flag_id=flag_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


# ── TENANT-LEVEL (timeline + notes) ──────────────────────────────────────

general_router = APIRouter(
    prefix="/api/v1/relationship-history",
    tags=["relationship-history"],
)


@general_router.post(
    "/timeline",
    response_model=TimelineEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_timeline_event(
    payload: TimelineEventCreate,
    current_user: CurrentUser = Depends(
        require_role("ems", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> TimelineEventResponse:
    return await svc.create_timeline_event(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )


@general_router.post(
    "/notes",
    response_model=InternalAccountNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_note(
    payload: InternalAccountNoteCreate,
    current_user: CurrentUser = Depends(
        require_role("ems", "admin", "founder")
    ),
    svc: RelationshipHistoryService = Depends(_svc),
) -> InternalAccountNoteResponse:
    return await svc.create_note(
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.user_id,
        payload=payload,
    )
