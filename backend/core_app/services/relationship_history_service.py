"""Relationship History Service — timelines, notes, warnings, snapshots.

Timeline entries preserve source and timestamp. Internal notes are
permission-controlled. Warning flags are visible but auditable.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.relationship_history import (
    FacilityWarningFlag,
    InternalAccountNote,
    PatientWarningFlag,
    RelationshipSummarySnapshot,
    RelationshipTimelineEvent,
)
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
    RelationshipSummaryResponse,
    TimelineEventCreate,
    TimelineEventListResponse,
    TimelineEventResponse,
    WarningFlagResolve,
)

logger = logging.getLogger(__name__)


class RelationshipHistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── TIMELINE EVENTS ───────────────────────────────────────────────────

    async def create_timeline_event(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: TimelineEventCreate,
    ) -> TimelineEventResponse:
        event = RelationshipTimelineEvent(
            tenant_id=tenant_id,
            patient_id=payload.patient_id,
            facility_id=payload.facility_id,
            event_type=payload.event_type,
            title=payload.title,
            description=payload.description,
            source=payload.source,
            source_entity_id=payload.source_entity_id,
            actor_user_id=actor_user_id,
            event_metadata=payload.metadata,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return TimelineEventResponse.model_validate(event)

    async def list_patient_timeline(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> TimelineEventListResponse:
        stmt = (
            select(RelationshipTimelineEvent)
            .where(
                RelationshipTimelineEvent.tenant_id == tenant_id,
                RelationshipTimelineEvent.patient_id == patient_id,
            )
            .order_by(RelationshipTimelineEvent.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return TimelineEventListResponse(
            items=[
                TimelineEventResponse.model_validate(e) for e in items
            ],
            total=len(items),
        )

    async def list_facility_timeline(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> TimelineEventListResponse:
        stmt = (
            select(RelationshipTimelineEvent)
            .where(
                RelationshipTimelineEvent.tenant_id == tenant_id,
                RelationshipTimelineEvent.facility_id == facility_id,
            )
            .order_by(RelationshipTimelineEvent.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return TimelineEventListResponse(
            items=[
                TimelineEventResponse.model_validate(e) for e in items
            ],
            total=len(items),
        )

    # ── INTERNAL NOTES ────────────────────────────────────────────────────

    async def create_note(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: InternalAccountNoteCreate,
    ) -> InternalAccountNoteResponse:
        note = InternalAccountNote(
            tenant_id=tenant_id,
            patient_id=payload.patient_id,
            facility_id=payload.facility_id,
            note_type=payload.note_type,
            content=payload.content,
            created_by_user_id=actor_user_id,
            is_sensitive=payload.is_sensitive,
            visibility=payload.visibility,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return InternalAccountNoteResponse.model_validate(note)

    async def list_patient_notes(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> InternalAccountNoteListResponse:
        stmt = (
            select(InternalAccountNote)
            .where(
                InternalAccountNote.tenant_id == tenant_id,
                InternalAccountNote.patient_id == patient_id,
            )
            .order_by(InternalAccountNote.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return InternalAccountNoteListResponse(
            items=[
                InternalAccountNoteResponse.model_validate(n)
                for n in items
            ],
            total=len(items),
        )

    # ── PATIENT WARNINGS ──────────────────────────────────────────────────

    async def create_patient_warning(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: PatientWarningFlagCreate,
    ) -> PatientWarningFlagResponse:
        flag = PatientWarningFlag(
            tenant_id=tenant_id,
            patient_id=patient_id,
            severity=payload.severity,
            flag_type=payload.flag_type,
            title=payload.title,
            description=payload.description,
            created_by_user_id=actor_user_id,
        )
        self.db.add(flag)
        await self.db.commit()
        await self.db.refresh(flag)
        return PatientWarningFlagResponse.model_validate(flag)

    async def list_patient_warnings(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> PatientWarningFlagListResponse:
        stmt = (
            select(PatientWarningFlag)
            .where(
                PatientWarningFlag.tenant_id == tenant_id,
                PatientWarningFlag.patient_id == patient_id,
            )
            .order_by(PatientWarningFlag.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return PatientWarningFlagListResponse(
            items=[
                PatientWarningFlagResponse.model_validate(f) for f in items
            ],
            total=len(items),
        )

    async def resolve_patient_warning(
        self,
        *,
        tenant_id: uuid.UUID,
        flag_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: WarningFlagResolve,
    ) -> PatientWarningFlagResponse:
        stmt = select(PatientWarningFlag).where(
            PatientWarningFlag.id == flag_id,
            PatientWarningFlag.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        flag = result.scalar_one_or_none()
        if not flag:
            raise AppError(
                code=ErrorCodes.NOT_FOUND, status_code=404,
                message="Patient warning flag not found",
            )
        flag.is_active = False
        flag.resolved_by_user_id = actor_user_id
        flag.resolution_notes = payload.resolution_notes
        await self.db.commit()
        await self.db.refresh(flag)
        return PatientWarningFlagResponse.model_validate(flag)

    # ── FACILITY WARNINGS ─────────────────────────────────────────────────

    async def create_facility_warning(
        self,
        *,
        tenant_id: uuid.UUID,
        facility_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FacilityWarningFlagCreate,
    ) -> FacilityWarningFlagResponse:
        flag = FacilityWarningFlag(
            tenant_id=tenant_id,
            facility_id=facility_id,
            severity=payload.severity,
            flag_type=payload.flag_type,
            title=payload.title,
            description=payload.description,
            created_by_user_id=actor_user_id,
        )
        self.db.add(flag)
        await self.db.commit()
        await self.db.refresh(flag)
        return FacilityWarningFlagResponse.model_validate(flag)

    async def list_facility_warnings(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> FacilityWarningFlagListResponse:
        stmt = (
            select(FacilityWarningFlag)
            .where(
                FacilityWarningFlag.tenant_id == tenant_id,
                FacilityWarningFlag.facility_id == facility_id,
            )
            .order_by(FacilityWarningFlag.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return FacilityWarningFlagListResponse(
            items=[
                FacilityWarningFlagResponse.model_validate(f)
                for f in items
            ],
            total=len(items),
        )

    async def resolve_facility_warning(
        self,
        *,
        tenant_id: uuid.UUID,
        flag_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: WarningFlagResolve,
    ) -> FacilityWarningFlagResponse:
        stmt = select(FacilityWarningFlag).where(
            FacilityWarningFlag.id == flag_id,
            FacilityWarningFlag.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        flag = result.scalar_one_or_none()
        if not flag:
            raise AppError(
                code=ErrorCodes.NOT_FOUND, status_code=404,
                message="Facility warning flag not found",
            )
        flag.is_active = False
        flag.resolved_by_user_id = actor_user_id
        flag.resolution_notes = payload.resolution_notes
        await self.db.commit()
        await self.db.refresh(flag)
        return FacilityWarningFlagResponse.model_validate(flag)

    # ── RELATIONSHIP SUMMARIES ────────────────────────────────────────────

    async def list_patient_summaries(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> RelationshipSummaryListResponse:
        stmt = (
            select(RelationshipSummarySnapshot)
            .where(
                RelationshipSummarySnapshot.tenant_id == tenant_id,
                RelationshipSummarySnapshot.patient_id == patient_id,
            )
            .order_by(RelationshipSummarySnapshot.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return RelationshipSummaryListResponse(
            items=[
                RelationshipSummaryResponse.model_validate(s)
                for s in items
            ],
            total=len(items),
        )
