"""Patient Identity Schemas — request/response DTOs for identity management."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.patient_identity import (
    DuplicateResolution,
    IdentifierSource,
    MergeRequestStatus,
    RelationshipFlagSeverity,
)

# ── ALIAS ─────────────────────────────────────────────────────────────────────


class PatientAliasCreate(BaseModel):
    alias_type: str = Field(..., max_length=64)
    first_name: str = Field(..., min_length=1, max_length=120)
    middle_name: str | None = Field(default=None, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    effective_date: date | None = None
    notes: str | None = None


class PatientAliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    alias_type: str
    first_name: str
    middle_name: str | None
    last_name: str
    effective_date: date | None
    notes: str | None
    created_at: datetime


# ── IDENTIFIER ────────────────────────────────────────────────────────────────


class PatientIdentifierCreate(BaseModel):
    source: IdentifierSource
    identifier_value: str = Field(..., min_length=1, max_length=128)
    issuing_authority: str | None = Field(default=None, max_length=255)
    provenance: str = Field(default="manual", max_length=64)


class PatientIdentifierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    source: IdentifierSource
    identifier_value: str
    issuing_authority: str | None
    provenance: str
    is_active: bool
    created_at: datetime


# ── DUPLICATE CANDIDATE ──────────────────────────────────────────────────────


class DuplicateCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_a_id: uuid.UUID
    patient_b_id: uuid.UUID
    confidence_score: float
    match_criteria: dict
    resolution: DuplicateResolution
    resolved_by_user_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


class DuplicateResolutionUpdate(BaseModel):
    resolution: DuplicateResolution
    notes: str | None = None


# ── MERGE REQUEST ─────────────────────────────────────────────────────────────


class MergeRequestCreate(BaseModel):
    source_patient_id: uuid.UUID
    target_patient_id: uuid.UUID
    merge_reason: str = Field(..., min_length=1)
    field_resolution_map: dict = Field(default_factory=dict)


class MergeRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_patient_id: uuid.UUID
    target_patient_id: uuid.UUID
    status: MergeRequestStatus
    requested_by_user_id: uuid.UUID
    reviewed_by_user_id: uuid.UUID | None
    merge_reason: str
    review_notes: str | None
    field_resolution_map: dict
    created_at: datetime
    updated_at: datetime


class MergeRequestReview(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    review_notes: str | None = None


# ── RELATIONSHIP FLAG ─────────────────────────────────────────────────────────


class RelationshipFlagCreate(BaseModel):
    flag_type: str = Field(..., max_length=64)
    severity: RelationshipFlagSeverity
    title: str = Field(..., max_length=255)
    description: str


class RelationshipFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    flag_type: str
    severity: RelationshipFlagSeverity
    title: str
    description: str
    is_active: bool
    created_by_user_id: uuid.UUID
    resolved_by_user_id: uuid.UUID | None
    resolution_notes: str | None
    created_at: datetime


class RelationshipFlagResolve(BaseModel):
    resolution_notes: str


# ── LIST RESPONSES ────────────────────────────────────────────────────────────


class PatientAliasListResponse(BaseModel):
    items: list[PatientAliasResponse]
    total: int


class PatientIdentifierListResponse(BaseModel):
    items: list[PatientIdentifierResponse]
    total: int


class DuplicateCandidateListResponse(BaseModel):
    items: list[DuplicateCandidateResponse]
    total: int


class MergeRequestListResponse(BaseModel):
    items: list[MergeRequestResponse]
    total: int


class RelationshipFlagListResponse(BaseModel):
    items: list[RelationshipFlagResponse]
    total: int
