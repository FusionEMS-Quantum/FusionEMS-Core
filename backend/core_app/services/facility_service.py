"""Facility Service — profile, contacts, notes, friction, service lines.

Facility data is tenant-scoped but reusable as external relationship records.
No silent overwrites. All changes are auditable.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.facility import (
    Facility,
    FacilityAuditEvent,
    FacilityContact,
    FacilityFrictionFlag,
    FacilityRelationshipNote,
    FacilityServiceProfile,
)
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

logger = logging.getLogger(__name__)


class FacilityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── FACILITY CRUD ─────────────────────────────────────────────────────

    async def create_facility(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FacilityCreate,
        correlation_id: str | None = None,
    ) -> FacilityResponse:
        facility = Facility(
            tenant_id=tenant_id,
            name=payload.name,
            facility_type=payload.facility_type,
            npi=payload.npi,
            address_line_1=payload.address_line_1,
            address_line_2=payload.address_line_2,
            city=payload.city,
            state=payload.state,
            zip_code=payload.zip_code,
            phone=payload.phone,
            fax=payload.fax,
            email=payload.email,
            destination_preference_notes=(
                payload.destination_preference_notes
            ),
            service_notes=payload.service_notes,
            version=1,
        )
        self.db.add(facility)
        self.db.add(FacilityAuditEvent(
            tenant_id=tenant_id,
            facility_id=facility.id,
            action="created",
            actor_user_id=actor_user_id,
            detail={"name": payload.name},
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(facility)
        return FacilityResponse.model_validate(facility)

    async def list_facilities(
        self, *, tenant_id: uuid.UUID
    ) -> FacilityListResponse:
        stmt = (
            select(Facility)
            .where(
                Facility.tenant_id == tenant_id,
                Facility.deleted_at.is_(None),
            )
            .order_by(Facility.name)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return FacilityListResponse(
            items=[FacilityResponse.model_validate(f) for f in items],
            total=len(items),
        )

    async def get_facility(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> FacilityResponse:
        facility = await self._get_facility(
            tenant_id=tenant_id, facility_id=facility_id
        )
        return FacilityResponse.model_validate(facility)

    async def update_facility(
        self,
        *,
        tenant_id: uuid.UUID,
        facility_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FacilityUpdate,
        correlation_id: str | None = None,
    ) -> FacilityResponse:
        facility = await self._get_facility(
            tenant_id=tenant_id, facility_id=facility_id
        )
        if facility.version != payload.version:
            raise AppError(
                code=ErrorCodes.CONFLICT, message="Version conflict"
            )
        for field in (
            "name", "facility_type", "npi",
            "address_line_1", "address_line_2", "city", "state",
            "zip_code", "phone", "fax", "email",
            "destination_preference_notes", "service_notes",
        ):
            setattr(facility, field, getattr(payload, field))
        if payload.relationship_state is not None:
            facility.relationship_state = payload.relationship_state
        facility.version += 1
        self.db.add(FacilityAuditEvent(
            tenant_id=tenant_id,
            facility_id=facility_id,
            action="updated",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(facility)
        return FacilityResponse.model_validate(facility)

    # ── CONTACTS ──────────────────────────────────────────────────────────

    async def add_contact(
        self,
        *,
        tenant_id: uuid.UUID,
        facility_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FacilityContactCreate,
        correlation_id: str | None = None,
    ) -> FacilityContactResponse:
        await self._get_facility(
            tenant_id=tenant_id, facility_id=facility_id
        )
        contact = FacilityContact(
            tenant_id=tenant_id,
            facility_id=facility_id,
            name=payload.name,
            role=payload.role,
            phone=payload.phone,
            email=payload.email,
            preferred_contact_method=payload.preferred_contact_method,
            notes=payload.notes,
        )
        self.db.add(contact)
        self.db.add(FacilityAuditEvent(
            tenant_id=tenant_id,
            facility_id=facility_id,
            action="contact_added",
            actor_user_id=actor_user_id,
            detail={"name": payload.name, "role": payload.role.value},
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(contact)
        return FacilityContactResponse.model_validate(contact)

    async def list_contacts(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> FacilityContactListResponse:
        stmt = (
            select(FacilityContact)
            .where(
                FacilityContact.tenant_id == tenant_id,
                FacilityContact.facility_id == facility_id,
            )
            .order_by(FacilityContact.name)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return FacilityContactListResponse(
            items=[
                FacilityContactResponse.model_validate(c) for c in items
            ],
            total=len(items),
        )

    # ── NOTES ─────────────────────────────────────────────────────────────

    async def add_note(
        self,
        *,
        tenant_id: uuid.UUID,
        facility_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FacilityRelationshipNoteCreate,
        correlation_id: str | None = None,
    ) -> FacilityRelationshipNoteResponse:
        await self._get_facility(
            tenant_id=tenant_id, facility_id=facility_id
        )
        note = FacilityRelationshipNote(
            tenant_id=tenant_id,
            facility_id=facility_id,
            note_type=payload.note_type,
            content=payload.content,
            created_by_user_id=actor_user_id,
            is_internal=payload.is_internal,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return FacilityRelationshipNoteResponse.model_validate(note)

    async def list_notes(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> FacilityRelationshipNoteListResponse:
        stmt = (
            select(FacilityRelationshipNote)
            .where(
                FacilityRelationshipNote.tenant_id == tenant_id,
                FacilityRelationshipNote.facility_id == facility_id,
            )
            .order_by(FacilityRelationshipNote.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return FacilityRelationshipNoteListResponse(
            items=[
                FacilityRelationshipNoteResponse.model_validate(n)
                for n in items
            ],
            total=len(items),
        )

    # ── SERVICE PROFILES ──────────────────────────────────────────────────

    async def add_service_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        facility_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FacilityServiceProfileCreate,
    ) -> FacilityServiceProfileResponse:
        await self._get_facility(
            tenant_id=tenant_id, facility_id=facility_id
        )
        profile = FacilityServiceProfile(
            tenant_id=tenant_id,
            facility_id=facility_id,
            service_line=payload.service_line,
            accepts_ems_transport=payload.accepts_ems_transport,
            average_turnaround_minutes=(
                payload.average_turnaround_minutes
            ),
            capability_notes=payload.capability_notes,
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return FacilityServiceProfileResponse.model_validate(profile)

    async def list_service_profiles(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> FacilityServiceProfileListResponse:
        stmt = (
            select(FacilityServiceProfile)
            .where(
                FacilityServiceProfile.tenant_id == tenant_id,
                FacilityServiceProfile.facility_id == facility_id,
            )
            .order_by(FacilityServiceProfile.service_line)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return FacilityServiceProfileListResponse(
            items=[
                FacilityServiceProfileResponse.model_validate(s)
                for s in items
            ],
            total=len(items),
        )

    # ── FRICTION FLAGS ────────────────────────────────────────────────────

    async def add_friction_flag(
        self,
        *,
        tenant_id: uuid.UUID,
        facility_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FacilityFrictionFlagCreate,
        correlation_id: str | None = None,
    ) -> FacilityFrictionFlagResponse:
        await self._get_facility(
            tenant_id=tenant_id, facility_id=facility_id
        )
        flag = FacilityFrictionFlag(
            tenant_id=tenant_id,
            facility_id=facility_id,
            category=payload.category,
            title=payload.title,
            description=payload.description,
            created_by_user_id=actor_user_id,
        )
        self.db.add(flag)
        self.db.add(FacilityAuditEvent(
            tenant_id=tenant_id,
            facility_id=facility_id,
            action="friction_flagged",
            actor_user_id=actor_user_id,
            detail={
                "category": payload.category.value,
                "title": payload.title,
            },
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(flag)
        return FacilityFrictionFlagResponse.model_validate(flag)

    async def list_friction_flags(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> FacilityFrictionFlagListResponse:
        stmt = (
            select(FacilityFrictionFlag)
            .where(
                FacilityFrictionFlag.tenant_id == tenant_id,
                FacilityFrictionFlag.facility_id == facility_id,
            )
            .order_by(FacilityFrictionFlag.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return FacilityFrictionFlagListResponse(
            items=[
                FacilityFrictionFlagResponse.model_validate(f)
                for f in items
            ],
            total=len(items),
        )

    async def resolve_friction_flag(
        self,
        *,
        tenant_id: uuid.UUID,
        flag_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: FrictionFlagResolve,
        correlation_id: str | None = None,
    ) -> FacilityFrictionFlagResponse:
        stmt = select(FacilityFrictionFlag).where(
            FacilityFrictionFlag.id == flag_id,
            FacilityFrictionFlag.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        flag = result.scalar_one_or_none()
        if not flag:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Friction flag not found",
            )
        flag.is_active = False
        flag.resolved_by_user_id = actor_user_id
        flag.resolution_notes = payload.resolution_notes
        self.db.add(FacilityAuditEvent(
            tenant_id=tenant_id,
            facility_id=flag.facility_id,
            action="friction_resolved",
            actor_user_id=actor_user_id,
            detail={"flag_id": str(flag_id)},
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(flag)
        return FacilityFrictionFlagResponse.model_validate(flag)

    # ── INTERNALS ─────────────────────────────────────────────────────────

    async def _get_facility(
        self, *, tenant_id: uuid.UUID, facility_id: uuid.UUID
    ) -> Facility:
        stmt = select(Facility).where(
            Facility.id == facility_id,
            Facility.tenant_id == tenant_id,
            Facility.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        facility = result.scalar_one_or_none()
        if not facility:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Facility not found",
            )
        return facility
