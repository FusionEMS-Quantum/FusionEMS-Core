"""Responsible Party Schemas — guarantor, subscriber, financial responsibility."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.responsible_party import (
    RelationshipToPatient,
    ResponsibilityState,
)

# ── RESPONSIBLE PARTY ─────────────────────────────────────────────────────────


class ResponsiblePartyCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    date_of_birth: date | None = None
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    zip_code: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ResponsiblePartyUpdate(ResponsiblePartyCreate):
    version: int = Field(ge=1)


class ResponsiblePartyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    first_name: str
    middle_name: str | None
    last_name: str
    date_of_birth: date | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    phone: str | None
    email: str | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


# ── LINK ──────────────────────────────────────────────────────────────────────


class PatientResponsiblePartyLinkCreate(BaseModel):
    responsible_party_id: uuid.UUID
    relationship_to_patient: RelationshipToPatient
    responsibility_state: ResponsibilityState = ResponsibilityState.UNKNOWN
    is_primary: bool = False
    effective_date: date | None = None
    end_date: date | None = None
    notes: str | None = None


class PatientResponsiblePartyLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    responsible_party_id: uuid.UUID
    relationship_to_patient: RelationshipToPatient
    responsibility_state: ResponsibilityState
    is_primary: bool
    effective_date: date | None
    end_date: date | None
    notes: str | None
    created_at: datetime


class ResponsibilityStateUpdate(BaseModel):
    responsibility_state: ResponsibilityState
    notes: str | None = None


# ── INSURANCE SUBSCRIBER ──────────────────────────────────────────────────────


class InsuranceSubscriberCreate(BaseModel):
    responsible_party_id: uuid.UUID
    insurance_carrier: str = Field(..., max_length=255)
    policy_number: str = Field(..., max_length=64)
    group_number: str | None = Field(default=None, max_length=64)
    member_id: str | None = Field(default=None, max_length=64)
    subscriber_name: str = Field(..., max_length=255)
    subscriber_dob: date | None = None
    relationship_to_subscriber: str | None = Field(
        default=None, max_length=32
    )
    effective_date: date | None = None
    termination_date: date | None = None


class InsuranceSubscriberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    responsible_party_id: uuid.UUID
    insurance_carrier: str
    policy_number: str
    group_number: str | None
    member_id: str | None
    subscriber_name: str
    subscriber_dob: date | None
    relationship_to_subscriber: str | None
    effective_date: date | None
    termination_date: date | None
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


# ── LIST RESPONSES ────────────────────────────────────────────────────────────


class ResponsiblePartyListResponse(BaseModel):
    items: list[ResponsiblePartyResponse]
    total: int


class PatientResponsiblePartyLinkListResponse(BaseModel):
    items: list[PatientResponsiblePartyLinkResponse]
    total: int


class InsuranceSubscriberListResponse(BaseModel):
    items: list[InsuranceSubscriberResponse]
    total: int
