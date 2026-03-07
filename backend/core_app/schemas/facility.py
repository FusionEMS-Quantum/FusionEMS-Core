"""Facility Schemas — profiles, contacts, service lines, friction flags."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.facility import (
    FacilityContactRole,
    FacilityRelationshipState,
    FacilityType,
    FrictionCategory,
)

# ── FACILITY ──────────────────────────────────────────────────────────────────


class FacilityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    facility_type: FacilityType
    npi: str | None = Field(default=None, max_length=20)
    address_line_1: str | None = Field(default=None, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    zip_code: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=20)
    fax: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    destination_preference_notes: str | None = None
    service_notes: str | None = None


class FacilityUpdate(FacilityCreate):
    version: int = Field(ge=1)
    relationship_state: FacilityRelationshipState | None = None


class FacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    facility_type: FacilityType
    npi: str | None
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    phone: str | None
    fax: str | None
    email: str | None
    relationship_state: FacilityRelationshipState
    destination_preference_notes: str | None
    service_notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


# ── FACILITY CONTACT ──────────────────────────────────────────────────────────


class FacilityContactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: FacilityContactRole
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    preferred_contact_method: str | None = Field(
        default=None, max_length=32
    )
    notes: str | None = None


class FacilityContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    facility_id: uuid.UUID
    name: str
    role: FacilityContactRole
    phone: str | None
    email: str | None
    preferred_contact_method: str | None
    notes: str | None
    is_active: bool
    created_at: datetime


# ── RELATIONSHIP NOTE ─────────────────────────────────────────────────────────


class FacilityRelationshipNoteCreate(BaseModel):
    note_type: str = Field(..., max_length=64)
    content: str = Field(..., min_length=1)
    is_internal: bool = True


class FacilityRelationshipNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    facility_id: uuid.UUID
    note_type: str
    content: str
    created_by_user_id: uuid.UUID
    is_internal: bool
    created_at: datetime


# ── SERVICE PROFILE ───────────────────────────────────────────────────────────


class FacilityServiceProfileCreate(BaseModel):
    service_line: str = Field(..., max_length=128)
    accepts_ems_transport: bool = True
    average_turnaround_minutes: int | None = None
    capability_notes: str | None = None


class FacilityServiceProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    facility_id: uuid.UUID
    service_line: str
    accepts_ems_transport: bool
    average_turnaround_minutes: int | None
    capability_notes: str | None
    is_active: bool
    created_at: datetime


# ── FRICTION FLAG ─────────────────────────────────────────────────────────────


class FacilityFrictionFlagCreate(BaseModel):
    category: FrictionCategory
    title: str = Field(..., max_length=255)
    description: str = Field(..., min_length=1)


class FacilityFrictionFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    facility_id: uuid.UUID
    category: FrictionCategory
    title: str
    description: str
    is_active: bool
    created_by_user_id: uuid.UUID
    resolved_by_user_id: uuid.UUID | None
    resolution_notes: str | None
    created_at: datetime


class FrictionFlagResolve(BaseModel):
    resolution_notes: str


# ── LIST RESPONSES ────────────────────────────────────────────────────────────


class FacilityListResponse(BaseModel):
    items: list[FacilityResponse]
    total: int


class FacilityContactListResponse(BaseModel):
    items: list[FacilityContactResponse]
    total: int


class FacilityRelationshipNoteListResponse(BaseModel):
    items: list[FacilityRelationshipNoteResponse]
    total: int


class FacilityServiceProfileListResponse(BaseModel):
    items: list[FacilityServiceProfileResponse]
    total: int


class FacilityFrictionFlagListResponse(BaseModel):
    items: list[FacilityFrictionFlagResponse]
    total: int
