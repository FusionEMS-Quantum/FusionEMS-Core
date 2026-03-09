"""Pydantic schemas for founder specialty, records, and integration command centers."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
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
    direction: Literal["INBOUND", "OUTBOUND"]
    state: Literal["QUEUED"] = "QUEUED"
    records_attempted: int = Field(default=0, ge=0)
    records_succeeded: int = Field(default=0, ge=0)
    records_failed: int = Field(default=0, ge=0)
    error_summary: dict[str, object] = Field(default_factory=dict)


class SyncDeadLetterCreateRequest(BaseModel):
    external_record_ref: str
    reason: str
    payload: dict[str, object] = Field(default_factory=dict)


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


class GrowthSummaryMetric(BaseModel):
    key: str
    value: int


class FounderGrowthSummary(BaseModel):
    generated_at: datetime
    conversion_events_total: int
    proposals_total: int
    proposals_pending: int
    active_subscriptions: int
    proposal_to_paid_conversion_pct: float
    pending_pipeline_cents: int
    active_mrr_cents: int
    pipeline_to_mrr_ratio: float
    graph_mailbox_configured: bool
    funnel_stage_counts: list[GrowthSummaryMetric]
    lead_tier_distribution: list[GrowthSummaryMetric]
    lead_score_buckets: list[GrowthSummaryMetric]
    integration_health: IntegrationCommandSummary


class GrowthConnectionStatus(BaseModel):
    service_key: str
    label: str
    required: bool
    connected: bool
    install_state: str
    permissions_state: str
    permission_errors: list[str] = Field(default_factory=list)
    token_state: str
    health_state: str
    last_successful_activity: datetime | None = None
    last_failed_activity: datetime | None = None
    retry_count: int = 0
    available_automations: list[str] = Field(default_factory=list)
    blocking_reason: str | None = None


class FounderGrowthSetupWizard(BaseModel):
    generated_at: datetime
    autopilot_ready: bool
    blocked_items: list[str] = Field(default_factory=list)
    services: list[GrowthConnectionStatus]


class LaunchOrchestratorStartRequest(BaseModel):
    mode: Literal["autopilot", "approval-first", "draft-only"] = "approval-first"
    auto_queue_sync_jobs: bool = True


class LaunchOrchestratorRunResponse(BaseModel):
    run_id: UUID
    mode: str
    queued_sync_jobs: int
    blocked_items: list[str]
    status: Literal["started", "blocked"]
    generated_at: datetime


class GrowthCampaignCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=3, max_length=1000)
    audience: dict[str, object] = Field(default_factory=dict)
    initial_platforms: list[str] = Field(default_factory=list)
    auto_generate_posts: bool = True


class GrowthCampaignResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    status: str
    objective: str
    audience: dict[str, object]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrowthSocialPostResponse(BaseModel):
    id: str
    tenant_id: str
    campaign_id: str
    platform: str
    content: str
    media_urls: list[str] = Field(default_factory=list)
    scheduled_for: datetime | None = None
    status: str
    post_metrics: dict[str, object] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrowthSocialPostStatusUpdateRequest(BaseModel):
    status: Literal["draft", "queued", "published", "failed", "approved"]


class GrowthAutomationResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    trigger_type: str
    flow_schema: dict[str, object]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GrowthDemoAssetGenerateRequest(BaseModel):
    focus_area: str = Field(min_length=3, max_length=200)
    campaign_id: str | None = None


class GrowthDemoAssetResponse(BaseModel):
    id: str
    tenant_id: str
    campaign_id: str | None = None
    asset_type: str
    content_url: str
    asset_metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
