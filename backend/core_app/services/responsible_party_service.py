"""Responsible Party Service — guarantor/subscriber management.

Patient identity is separate from billing responsibility. A patient may not
be the financially responsible party. All changes are auditable.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.responsible_party import (
    InsuranceSubscriberProfile,
    PatientResponsiblePartyLink,
    ResponsibilityAuditEvent,
    ResponsibleParty,
)
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

logger = logging.getLogger(__name__)


class ResponsiblePartyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── RESPONSIBLE PARTY CRUD ────────────────────────────────────────────

    async def create_responsible_party(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: ResponsiblePartyCreate,
        correlation_id: str | None = None,
    ) -> ResponsiblePartyResponse:
        party = ResponsibleParty(
            tenant_id=tenant_id,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
            address_line_1=payload.address_line_1,
            address_line_2=payload.address_line_2,
            city=payload.city,
            state=payload.state,
            zip_code=payload.zip_code,
            phone=payload.phone,
            email=payload.email,
            notes=payload.notes,
            version=1,
        )
        self.db.add(party)
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="responsible_party_created",
            entity_name="ResponsibleParty",
            entity_id=party.id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(party)
        return ResponsiblePartyResponse.model_validate(party)

    async def list_responsible_parties(
        self, *, tenant_id: uuid.UUID
    ) -> ResponsiblePartyListResponse:
        stmt = (
            select(ResponsibleParty)
            .where(ResponsibleParty.tenant_id == tenant_id)
            .order_by(ResponsibleParty.last_name)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return ResponsiblePartyListResponse(
            items=[
                ResponsiblePartyResponse.model_validate(p) for p in items
            ],
            total=len(items),
        )

    async def get_responsible_party(
        self, *, tenant_id: uuid.UUID, party_id: uuid.UUID
    ) -> ResponsiblePartyResponse:
        stmt = select(ResponsibleParty).where(
            ResponsibleParty.id == party_id,
            ResponsibleParty.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        party = result.scalar_one_or_none()
        if not party:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Responsible party not found",
            )
        return ResponsiblePartyResponse.model_validate(party)

    async def update_responsible_party(
        self,
        *,
        tenant_id: uuid.UUID,
        party_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: ResponsiblePartyUpdate,
        correlation_id: str | None = None,
    ) -> ResponsiblePartyResponse:
        stmt = select(ResponsibleParty).where(
            ResponsibleParty.id == party_id,
            ResponsibleParty.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        party = result.scalar_one_or_none()
        if not party:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Responsible party not found",
            )
        if party.version != payload.version:
            raise AppError(
                code=ErrorCodes.CONFLICT,
                message="Version conflict",
            )
        for field in (
            "first_name", "middle_name", "last_name",
            "date_of_birth", "address_line_1", "address_line_2",
            "city", "state", "zip_code", "phone", "email", "notes",
        ):
            setattr(party, field, getattr(payload, field))
        party.version += 1
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="responsible_party_updated",
            entity_name="ResponsibleParty",
            entity_id=party_id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(party)
        return ResponsiblePartyResponse.model_validate(party)

    # ── PATIENT LINK ──────────────────────────────────────────────────────

    async def link_to_patient(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: PatientResponsiblePartyLinkCreate,
        correlation_id: str | None = None,
    ) -> PatientResponsiblePartyLinkResponse:
        link = PatientResponsiblePartyLink(
            tenant_id=tenant_id,
            patient_id=patient_id,
            responsible_party_id=payload.responsible_party_id,
            relationship_to_patient=payload.relationship_to_patient,
            responsibility_state=payload.responsibility_state,
            is_primary=payload.is_primary,
            effective_date=payload.effective_date,
            end_date=payload.end_date,
            notes=payload.notes,
        )
        self.db.add(link)
        self.db.add(ResponsibilityAuditEvent(
            tenant_id=tenant_id,
            patient_id=patient_id,
            responsible_party_id=payload.responsible_party_id,
            action="linked",
            new_state=payload.responsibility_state.value,
            actor_user_id=actor_user_id,
            detail={
                "relationship": payload.relationship_to_patient.value,
            },
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(link)
        return PatientResponsiblePartyLinkResponse.model_validate(link)

    async def list_patient_links(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> PatientResponsiblePartyLinkListResponse:
        stmt = (
            select(PatientResponsiblePartyLink)
            .where(
                PatientResponsiblePartyLink.tenant_id == tenant_id,
                PatientResponsiblePartyLink.patient_id == patient_id,
            )
            .order_by(PatientResponsiblePartyLink.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return PatientResponsiblePartyLinkListResponse(
            items=[
                PatientResponsiblePartyLinkResponse.model_validate(link)
                for link in items
            ],
            total=len(items),
        )

    async def update_responsibility_state(
        self,
        *,
        tenant_id: uuid.UUID,
        link_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: ResponsibilityStateUpdate,
        correlation_id: str | None = None,
    ) -> PatientResponsiblePartyLinkResponse:
        stmt = select(PatientResponsiblePartyLink).where(
            PatientResponsiblePartyLink.id == link_id,
            PatientResponsiblePartyLink.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        link = result.scalar_one_or_none()
        if not link:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Responsibility link not found",
            )
        prev_state = link.responsibility_state.value
        link.responsibility_state = payload.responsibility_state
        link.notes = payload.notes or link.notes
        self.db.add(ResponsibilityAuditEvent(
            tenant_id=tenant_id,
            patient_id=link.patient_id,
            responsible_party_id=link.responsible_party_id,
            action="state_changed",
            previous_state=prev_state,
            new_state=payload.responsibility_state.value,
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(link)
        return PatientResponsiblePartyLinkResponse.model_validate(link)

    # ── INSURANCE SUBSCRIBER ──────────────────────────────────────────────

    async def create_subscriber_profile(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: InsuranceSubscriberCreate,
        correlation_id: str | None = None,
    ) -> InsuranceSubscriberResponse:
        profile = InsuranceSubscriberProfile(
            tenant_id=tenant_id,
            responsible_party_id=payload.responsible_party_id,
            insurance_carrier=payload.insurance_carrier,
            policy_number=payload.policy_number,
            group_number=payload.group_number,
            member_id=payload.member_id,
            subscriber_name=payload.subscriber_name,
            subscriber_dob=payload.subscriber_dob,
            relationship_to_subscriber=(
                payload.relationship_to_subscriber
            ),
            effective_date=payload.effective_date,
            termination_date=payload.termination_date,
            version=1,
        )
        self.db.add(profile)
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="subscriber_profile_created",
            entity_name="InsuranceSubscriberProfile",
            entity_id=profile.id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(profile)
        return InsuranceSubscriberResponse.model_validate(profile)

    async def list_subscriber_profiles(
        self, *, tenant_id: uuid.UUID, party_id: uuid.UUID
    ) -> InsuranceSubscriberListResponse:
        stmt = (
            select(InsuranceSubscriberProfile)
            .where(
                InsuranceSubscriberProfile.tenant_id == tenant_id,
                InsuranceSubscriberProfile.responsible_party_id == party_id,
            )
            .order_by(InsuranceSubscriberProfile.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return InsuranceSubscriberListResponse(
            items=[
                InsuranceSubscriberResponse.model_validate(s) for s in items
            ],
            total=len(items),
        )

    # ── AUDIT ─────────────────────────────────────────────────────────────

    async def _audit(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        action: str,
        entity_name: str,
        entity_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> None:
        self.db.add(AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            correlation_id=correlation_id,
        ))
