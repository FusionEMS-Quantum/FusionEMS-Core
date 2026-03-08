"""Contact Preference Schemas — communication channel preferences and opt-outs."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.contact_preference import (
    ContactChannel,
    OptOutReason,
)

# ── CONTACT PREFERENCE ───────────────────────────────────────────────────────


class ContactPreferenceUpsert(BaseModel):
    patient_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    sms_allowed: bool = False
    call_allowed: bool = False
    email_allowed: bool = False
    mail_required: bool = False
    contact_restricted: bool = False
    preferred_channel: ContactChannel | None = None
    preferred_time_start: str | None = Field(
        default=None, max_length=8
    )
    preferred_time_end: str | None = Field(
        default=None, max_length=8
    )
    facility_callback_preference: str | None = Field(
        default=None, max_length=128
    )
    notes: str | None = None


class ContactPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    sms_allowed: bool
    call_allowed: bool
    email_allowed: bool
    mail_required: bool
    contact_restricted: bool
    preferred_channel: ContactChannel | None
    preferred_time_start: str | None
    preferred_time_end: str | None
    facility_callback_preference: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


# ── OPT OUT EVENT ─────────────────────────────────────────────────────────────


class OptOutEventCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    channel: ContactChannel
    action: str = Field(..., pattern="^(opt_in|opt_out)$")
    reason: OptOutReason
    notes: str | None = None


class OptOutEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    channel: ContactChannel
    action: str
    reason: OptOutReason
    actor_user_id: uuid.UUID
    notes: str | None
    created_at: datetime


# ── LANGUAGE PREFERENCE ───────────────────────────────────────────────────────


class LanguagePreferenceUpsert(BaseModel):
    primary_language: str = Field(default="en", max_length=32)
    secondary_language: str | None = Field(
        default=None, max_length=32
    )
    interpreter_required: bool = False
    interpreter_language: str | None = Field(
        default=None, max_length=32
    )
    notes: str | None = None


class LanguagePreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    primary_language: str
    secondary_language: str | None
    interpreter_required: bool
    interpreter_language: str | None
    notes: str | None
    created_at: datetime


# ── LIST RESPONSES ────────────────────────────────────────────────────────────


class ContactPreferenceListResponse(BaseModel):
    items: list[ContactPreferenceResponse]
    total: int


class OptOutEventListResponse(BaseModel):
    items: list[OptOutEventResponse]
    total: int


# ── CONTACT POLICY AUDIT EVENT ────────────────────────────────────────────────


class ContactPolicyAuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    action: str
    previous_state: dict
    new_state: dict
    actor_user_id: uuid.UUID
    correlation_id: str | None
    created_at: datetime


class ContactPolicyAuditEventListResponse(BaseModel):
    items: list[ContactPolicyAuditEventResponse]
    total: int
