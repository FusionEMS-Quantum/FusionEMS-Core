"""Schemas for the third-party billing export / offboarding system."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ── Export Package Types ─────────────────────────────────────────────────────

class ExportModuleType(StrEnum):
    CLINICAL = "CLINICAL"
    BILLING = "BILLING"
    OPERATIONS = "OPERATIONS"
    COMMUNICATIONS = "COMMUNICATIONS"
    DOCUMENTS = "DOCUMENTS"
    FULL_OFFBOARDING = "FULL_OFFBOARDING"


class ExportPackageState(StrEnum):
    REQUESTED = "REQUESTED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    BUILDING = "BUILDING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    REBUILT = "REBUILT"


class OffboardingRiskLevel(StrEnum):
    READY_FOR_HANDOFF = "READY_FOR_HANDOFF"
    DATA_GAPS_DETECTED = "DATA_GAPS_DETECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_HANDOFF_RISK = "HIGH_HANDOFF_RISK"
    PACKAGE_INCOMPLETE = "PACKAGE_INCOMPLETE"


class HandoffDeliveryMethod(StrEnum):
    SECURE_LINK = "SECURE_LINK"
    S3_BUCKET = "S3_BUCKET"
    SFTP = "SFTP"


# ── Request Schemas ──────────────────────────────────────────────────────────

class ExportPackageCreateRequest(BaseModel):
    """Create a new export package request."""
    modules: list[ExportModuleType] = Field(min_length=1)
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    patient_scope: list[uuid.UUID] | None = Field(default=None, description="Limit to specific patients")
    account_scope: list[uuid.UUID] | None = Field(default=None, description="Limit to specific AR accounts")
    include_attachments: bool = True
    include_field_crosswalk: bool = True
    delivery_method: HandoffDeliveryMethod = HandoffDeliveryMethod.SECURE_LINK
    delivery_target: str | None = Field(default=None, description="S3 bucket ARN or SFTP host if applicable")
    notes: str | None = Field(default=None, max_length=2000)


class ExportPackageApproveRequest(BaseModel):
    """Approve or reject a pending export package."""
    approved: bool
    reviewer_notes: str | None = Field(default=None, max_length=2000)


class OffboardingStartRequest(BaseModel):
    """Initiate a full offboarding sequence."""
    reason: str = Field(min_length=2, max_length=1000)
    target_vendor: str | None = Field(default=None, max_length=255)
    requested_completion_date: datetime | None = None
    modules: list[ExportModuleType] = Field(
        default_factory=lambda: [ExportModuleType.FULL_OFFBOARDING],
    )
    delivery_method: HandoffDeliveryMethod = HandoffDeliveryMethod.SECURE_LINK
    delivery_target: str | None = None
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)


class SecureLinkAccessRequest(BaseModel):
    """Request to generate or revoke a secure download link."""
    package_id: uuid.UUID
    action: str = Field(pattern=r"^(generate|revoke|reissue)$")
    expires_hours: int = Field(default=72, ge=1, le=720)


# ── Response Schemas ─────────────────────────────────────────────────────────

class ExportPackageResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    state: ExportPackageState
    modules: list[str]
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    delivery_method: str
    delivery_target: str | None = None
    include_attachments: bool
    include_field_crosswalk: bool
    requested_by: uuid.UUID
    approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
    package_s3_key: str | None = None
    secure_link: str | None = None
    secure_link_expires_at: datetime | None = None
    manifest: dict[str, Any] | None = None
    integrity_hash: str | None = None
    risk_level: OffboardingRiskLevel | None = None
    risk_details: list[str] | None = None
    file_count: int | None = None
    total_size_bytes: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ExportPackageSummary(BaseModel):
    id: uuid.UUID
    state: ExportPackageState
    modules: list[str]
    risk_level: OffboardingRiskLevel | None = None
    created_at: datetime
    file_count: int | None = None
    total_size_bytes: int | None = None


class OffboardingStatusResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    state: ExportPackageState
    reason: str
    target_vendor: str | None = None
    requested_completion_date: datetime | None = None
    risk_level: OffboardingRiskLevel | None = None
    risk_details: list[str] | None = None
    packages: list[ExportPackageSummary] = []
    created_at: datetime
    updated_at: datetime


class FieldCrosswalkEntry(BaseModel):
    internal_field: str
    export_field: str
    business_meaning: str
    destination_file: str
    data_type: str
    required: bool
    import_note: str | None = None


class SecureLinkResponse(BaseModel):
    package_id: uuid.UUID
    download_url: str | None = None
    expires_at: datetime | None = None
    revoked: bool = False
    access_log_count: int = 0


class PortalDashboardResponse(BaseModel):
    clean_claim_rate_pct: float
    claims_ready_to_submit: int
    claims_blocked: int
    denied_claims: int
    appeals_in_progress: int
    patient_balances_open: int
    payment_plan_count: int
    documentation_gaps: int
    certification_gaps: int
    export_readiness: str
    offboarding_status: str | None = None
    communication_activity: int
    secure_handoff_ready: bool
    top_actions: list[dict[str, Any]]


class PortalClaimRow(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    patient_id: uuid.UUID
    status: str
    payer_name: str | None = None
    total_billed_cents: int
    insurance_paid_cents: int
    patient_responsibility_cents: int
    aging_days: int
    is_valid: bool
    appeal_status: str | None = None
    documentation_complete: bool
    export_eligible: bool
    next_best_action: str | None = None
    created_at: datetime


class PortalClaimDetail(BaseModel):
    claim: PortalClaimRow
    submission_history: list[dict[str, Any]]
    denial_reasons: list[str]
    audit_trail: list[dict[str, Any]]
    linked_communications: list[dict[str, Any]]
    documentation_status: dict[str, Any]


class ExportAccessLog(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    accessed_by: uuid.UUID
    access_type: str
    ip_address: str | None = None
    user_agent: str | None = None
    accessed_at: datetime


class HandoffRiskItem(BaseModel):
    category: str
    description: str
    severity: str
    count: int | None = None
    affected_ids: list[str] | None = None
