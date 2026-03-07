"""Contact Preference Service — channel preferences, opt-in/out, language.

Contact permissions are explicit. Preference changes are logged via
ContactPolicyAuditEvent. Billing communications respect preference state.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.contact_preference import (
    CommunicationOptOutEvent,
    ContactPolicyAuditEvent,
    ContactPreference,
    LanguagePreference,
)
from core_app.schemas.contact_preference import (
    ContactPreferenceResponse,
    ContactPreferenceUpsert,
    LanguagePreferenceResponse,
    LanguagePreferenceUpsert,
    OptOutEventCreate,
    OptOutEventListResponse,
    OptOutEventResponse,
)

logger = logging.getLogger(__name__)


class ContactPreferenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── CONTACT PREFERENCES ───────────────────────────────────────────────

    async def upsert_preference(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: ContactPreferenceUpsert,
        correlation_id: str | None = None,
    ) -> ContactPreferenceResponse:
        # Check for existing preference
        stmt = select(ContactPreference).where(
            ContactPreference.tenant_id == tenant_id,
            ContactPreference.patient_id == payload.patient_id,
            ContactPreference.facility_id == payload.facility_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            previous_state = {
                "sms_allowed": existing.sms_allowed,
                "call_allowed": existing.call_allowed,
                "email_allowed": existing.email_allowed,
                "mail_required": existing.mail_required,
                "contact_restricted": existing.contact_restricted,
            }
            for field in (
                "sms_allowed", "call_allowed", "email_allowed",
                "mail_required", "contact_restricted",
                "preferred_channel", "preferred_time_start",
                "preferred_time_end",
                "facility_callback_preference", "notes",
            ):
                setattr(existing, field, getattr(payload, field))
            existing.version += 1
            new_state = {
                "sms_allowed": existing.sms_allowed,
                "call_allowed": existing.call_allowed,
                "email_allowed": existing.email_allowed,
                "mail_required": existing.mail_required,
                "contact_restricted": existing.contact_restricted,
            }
            self.db.add(ContactPolicyAuditEvent(
                tenant_id=tenant_id,
                patient_id=payload.patient_id,
                facility_id=payload.facility_id,
                action="preference_updated",
                previous_state=previous_state,
                new_state=new_state,
                actor_user_id=actor_user_id,
                correlation_id=correlation_id,
            ))
            await self.db.commit()
            await self.db.refresh(existing)
            return ContactPreferenceResponse.model_validate(existing)

        pref = ContactPreference(
            tenant_id=tenant_id,
            patient_id=payload.patient_id,
            facility_id=payload.facility_id,
            sms_allowed=payload.sms_allowed,
            call_allowed=payload.call_allowed,
            email_allowed=payload.email_allowed,
            mail_required=payload.mail_required,
            contact_restricted=payload.contact_restricted,
            preferred_channel=payload.preferred_channel,
            preferred_time_start=payload.preferred_time_start,
            preferred_time_end=payload.preferred_time_end,
            facility_callback_preference=(
                payload.facility_callback_preference
            ),
            notes=payload.notes,
            version=1,
        )
        self.db.add(pref)
        self.db.add(ContactPolicyAuditEvent(
            tenant_id=tenant_id,
            patient_id=payload.patient_id,
            facility_id=payload.facility_id,
            action="preference_created",
            previous_state={},
            new_state={
                "sms_allowed": payload.sms_allowed,
                "call_allowed": payload.call_allowed,
                "email_allowed": payload.email_allowed,
                "mail_required": payload.mail_required,
                "contact_restricted": payload.contact_restricted,
            },
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
        ))
        await self.db.commit()
        await self.db.refresh(pref)
        return ContactPreferenceResponse.model_validate(pref)

    async def get_patient_preference(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> ContactPreferenceResponse | None:
        stmt = select(ContactPreference).where(
            ContactPreference.tenant_id == tenant_id,
            ContactPreference.patient_id == patient_id,
        )
        result = await self.db.execute(stmt)
        pref = result.scalar_one_or_none()
        if not pref:
            return None
        return ContactPreferenceResponse.model_validate(pref)

    # ── OPT-OUT EVENTS ────────────────────────────────────────────────────

    async def record_opt_out(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: OptOutEventCreate,
    ) -> OptOutEventResponse:
        event = CommunicationOptOutEvent(
            tenant_id=tenant_id,
            patient_id=payload.patient_id,
            facility_id=payload.facility_id,
            channel=payload.channel,
            action=payload.action,
            reason=payload.reason,
            actor_user_id=actor_user_id,
            notes=payload.notes,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return OptOutEventResponse.model_validate(event)

    async def list_opt_out_events(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> OptOutEventListResponse:
        stmt = (
            select(CommunicationOptOutEvent)
            .where(
                CommunicationOptOutEvent.tenant_id == tenant_id,
                CommunicationOptOutEvent.patient_id == patient_id,
            )
            .order_by(CommunicationOptOutEvent.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return OptOutEventListResponse(
            items=[
                OptOutEventResponse.model_validate(e) for e in items
            ],
            total=len(items),
        )

    # ── LANGUAGE PREFERENCES ──────────────────────────────────────────────

    async def upsert_language_preference(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: LanguagePreferenceUpsert,
    ) -> LanguagePreferenceResponse:
        stmt = select(LanguagePreference).where(
            LanguagePreference.tenant_id == tenant_id,
            LanguagePreference.patient_id == patient_id,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            for field in (
                "primary_language", "secondary_language",
                "interpreter_required", "interpreter_language",
                "notes",
            ):
                setattr(existing, field, getattr(payload, field))
            await self.db.commit()
            await self.db.refresh(existing)
            return LanguagePreferenceResponse.model_validate(existing)

        pref = LanguagePreference(
            tenant_id=tenant_id,
            patient_id=patient_id,
            primary_language=payload.primary_language,
            secondary_language=payload.secondary_language,
            interpreter_required=payload.interpreter_required,
            interpreter_language=payload.interpreter_language,
            notes=payload.notes,
        )
        self.db.add(pref)
        await self.db.commit()
        await self.db.refresh(pref)
        return LanguagePreferenceResponse.model_validate(pref)

    async def get_language_preference(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> LanguagePreferenceResponse | None:
        stmt = select(LanguagePreference).where(
            LanguagePreference.tenant_id == tenant_id,
            LanguagePreference.patient_id == patient_id,
        )
        result = await self.db.execute(stmt)
        pref = result.scalar_one_or_none()
        if not pref:
            return None
        return LanguagePreferenceResponse.model_validate(pref)
