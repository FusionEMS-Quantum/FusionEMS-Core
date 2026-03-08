"""Pydantic schemas for founder specialty, records, and integration command centers."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FounderCommandAction(BaseModel):
    domain: str
    severity: str
    summary: str
    recommended_action: str
    entity_id: UUID | None = None


class SpecialtyOpsSummary(BaseModel):
    preplan_gaps: int
    active_hazard_flags: int
    pending_lz_confirmations: int
    duty_time_warnings: int
    specialty_missions_blocked: int
    mission_packet_failures: int
    top_actions: list[FounderCommandAction]


class RecordsCommandSummary(BaseModel):
    draft_or_unsealed_records: int
    signature_gaps: int
    low_confidence_ocr_results: int
    chain_of_custody_anomalies: int
    pending_release_authorizations: int
    failed_record_exports: int
    open_qa_exceptions: int
    top_actions: list[FounderCommandAction]


class IntegrationCommandSummary(BaseModel):
    degraded_or_disabled_installs: int
    failed_sync_jobs_24h: int
    dead_letter_records_24h: int
    pending_webhook_retries: int
    revoked_or_rotating_api_credentials: int
    quota_denial_windows_24h: int
    top_actions: list[FounderCommandAction]


class ConnectorSyncJobResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_connector_install_id: UUID
    direction: str
    state: str
    started_at: datetime | None
    completed_at: datetime | None
    records_attempted: int
    records_succeeded: int
    records_failed: int
    error_summary: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectorSyncJobCreateRequest(BaseModel):
    tenant_connector_install_id: UUID
    direction: str
    state: str = "QUEUED"
    records_attempted: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    error_summary: dict = Field(default_factory=dict)


class SyncDeadLetterCreateRequest(BaseModel):
    external_record_ref: str
    reason: str
    payload: dict = Field(default_factory=dict)


class SyncDeadLetterResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    connector_sync_job_id: UUID
    external_record_ref: str
    reason: str
    payload: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordExportResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    clinical_record_id: UUID
    destination_system: str
    state: str
    queued_at: datetime
    delivered_at: datetime | None
    failure_reason: str | None
    delivery_payload: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlightMissionResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    mission_number: str
    air_asset_id: UUID | None
    state: str
    origin: str | None
    destination: str | None
    receiving_facility_notes: str | None
    scheduled_departure_at: datetime | None
    actual_departure_at: datetime | None
    actual_arrival_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
