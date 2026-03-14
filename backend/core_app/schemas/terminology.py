from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TerminologyCodeSystemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_uri: str = Field(min_length=1, max_length=255)
    system_version: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=255)
    publisher: str | None = Field(default=None, max_length=255)
    status: str = Field(default="active", max_length=32)
    is_external: bool = True
    metadata_blob: dict = Field(default_factory=dict)


class TerminologyCodeSystemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    system_uri: str
    system_version: str
    name: str
    publisher: str | None
    status: str
    is_external: bool
    metadata_blob: dict
    version: int
    created_at: datetime
    updated_at: datetime


class TerminologyConceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    code_system_id: uuid.UUID
    code: str
    display: str
    definition: str | None
    active: bool
    effective_start_date: date | None
    effective_end_date: date | None
    properties: dict
    version: int
    created_at: datetime
    updated_at: datetime


class TerminologyConceptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    display: str = Field(min_length=1, max_length=512)
    definition: str | None = None
    active: bool = True
    effective_start_date: date | None = None
    effective_end_date: date | None = None
    properties: dict = Field(default_factory=dict)


class TerminologyConceptBulkUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code_system_id: uuid.UUID
    concepts: list[TerminologyConceptCreate] = Field(min_length=1, max_length=10000)


class TerminologySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[TerminologyConceptResponse]


class TerminologyAutocompleteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestions: list[TerminologyConceptResponse]


class TerminologyMappingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_concept_id: uuid.UUID
    to_concept_id: uuid.UUID
    map_type: str = Field(default="equivalent", max_length=32)
    source: str = Field(default="manual", max_length=64)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata_blob: dict = Field(default_factory=dict)


class TerminologyMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    from_concept_id: uuid.UUID
    to_concept_id: uuid.UUID
    map_type: str
    source: str
    confidence: float | None
    is_active: bool
    metadata_blob: dict
    version: int
    created_at: datetime
    updated_at: datetime


class TerminologyExternalLookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    q: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=25, ge=1, le=100)


class NihClinicalTablesResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    display: str
    extra: dict = Field(default_factory=dict)


class NihClinicalTablesLookupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[NihClinicalTablesResult]


class RxNavNormalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)


class RxNavNormalizeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rxnorm_cui: str | None = None
    normalized_name: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    result: dict = Field(default_factory=dict)


class NpiLookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=200)
    npi: str | None = Field(default=None, max_length=10)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=2)
    limit: int = Field(default=10, ge=1, le=50)


class NpiLookupResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[dict]
