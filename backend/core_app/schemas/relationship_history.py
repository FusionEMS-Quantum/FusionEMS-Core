"""Relationship History Schemas — timelines, notes, warnings, snapshots."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.relationship_history import (
    TimelineEventType,
    WarningFlagSeverity,
)

# ── TIMELINE EVENT ────────────────────────────────────────────────────────────


class TimelineEventCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    event_type: TimelineEventType
    title: str = Field(..., max_length=255)
    description: str = Field(..., min_length=1)
    source: str = Field(default="user", max_length=64)
    source_entity_id: uuid.UUID | None = None
    metadata: dict = Field(default_factory=dict)


class TimelineEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    event_type: TimelineEventType
    title: str
    description: str
    source: str
    source_entity_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    metadata: dict
    created_at: datetime


# ── INTERNAL ACCOUNT NOTE ────────────────────────────────────────────────────


class InternalAccountNoteCreate(BaseModel):
    patient_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    note_type: str = Field(..., max_length=64)
    content: str = Field(..., min_length=1)
    is_sensitive: bool = False
    visibility: str = Field(default="internal", max_length=32)


class InternalAccountNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    note_type: str
    content: str
    created_by_user_id: uuid.UUID
    is_sensitive: bool
    visibility: str
    created_at: datetime


# ── PATIENT WARNING FLAG ──────────────────────────────────────────────────────


class PatientWarningFlagCreate(BaseModel):
    severity: WarningFlagSeverity
    flag_type: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    description: str = Field(..., min_length=1)


class PatientWarningFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    severity: WarningFlagSeverity
    flag_type: str
    title: str
    description: str
    is_active: bool
    created_by_user_id: uuid.UUID
    resolved_by_user_id: uuid.UUID | None
    resolution_notes: str | None
    created_at: datetime


# ── FACILITY WARNING FLAG ─────────────────────────────────────────────────────


class FacilityWarningFlagCreate(BaseModel):
    severity: WarningFlagSeverity
    flag_type: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    description: str = Field(..., min_length=1)


class FacilityWarningFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    facility_id: uuid.UUID
    severity: WarningFlagSeverity
    flag_type: str
    title: str
    description: str
    is_active: bool
    created_by_user_id: uuid.UUID
    resolved_by_user_id: uuid.UUID | None
    resolution_notes: str | None
    created_at: datetime


class WarningFlagResolve(BaseModel):
    resolution_notes: str


# ── RELATIONSHIP SUMMARY ─────────────────────────────────────────────────────


class RelationshipSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    summary_type: str
    content: str
    source: str
    model_version: str | None
    confidence_score: float | None
    event_count: int
    created_at: datetime


# ── LIST RESPONSES ────────────────────────────────────────────────────────────


class TimelineEventListResponse(BaseModel):
    items: list[TimelineEventResponse]
    total: int


class InternalAccountNoteListResponse(BaseModel):
    items: list[InternalAccountNoteResponse]
    total: int


class PatientWarningFlagListResponse(BaseModel):
    items: list[PatientWarningFlagResponse]
    total: int


class FacilityWarningFlagListResponse(BaseModel):
    items: list[FacilityWarningFlagResponse]
    total: int


class RelationshipSummaryListResponse(BaseModel):
    items: list[RelationshipSummaryResponse]
    total: int
