"""
Document Vault — Pydantic Schemas

Request / response models for the Founder-Only Document Manager API.
All timestamps are UTC ISO-8601.  UUIDs are strings in responses.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Vault definition (read-only catalog)
# ---------------------------------------------------------------------------

class VaultDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vault_id: str
    display_name: str
    description: str
    s3_prefix: str
    retention_class: str
    retention_years: int | None
    retention_days: int | None
    is_permanent: bool
    requires_legal_hold_review: bool
    icon_key: str
    sort_order: int
    document_count: int = Field(default=0, description="Injected by service layer")


# ---------------------------------------------------------------------------
# Document record
# ---------------------------------------------------------------------------

class DocumentSummaryOut(BaseModel):
    """Lightweight list-view payload."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vault_id: str
    title: str
    original_filename: str
    content_type: str
    file_size_bytes: int | None
    lock_state: str
    retention_class: str | None
    retain_until: datetime | None
    ocr_status: str
    ai_classification_status: str
    ai_document_type: str | None
    ai_tags: list[str] | None
    uploaded_by_display: str | None
    created_at: datetime
    updated_at: datetime


class DocumentDetailOut(DocumentSummaryOut):
    """Full detail including OCR text, AI summary, addenda, lock history, metadata."""
    s3_bucket: str
    s3_key: str
    checksum_sha256: str | None
    ocr_text: str | None
    ai_summary: str | None
    ai_confidence: float | None
    ai_classified_at: datetime | None
    ocr_completed_at: datetime | None
    doc_metadata: dict[str, Any]
    addenda: list[dict[str, Any]]
    lock_history: list[dict[str, Any]]


class DocumentUploadInitRequest(BaseModel):
    """Initiate a presigned S3 upload for a document."""
    vault_id: str = Field(..., description="Target vault identifier")
    title: str = Field(..., min_length=1, max_length=512)
    original_filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=1, max_length=128)
    file_size_bytes: int | None = Field(None, gt=0)
    doc_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("vault_id")
    @classmethod
    def vault_id_must_be_known(cls, v: str) -> str:
        known = {
            "legal_corporate", "tax_financial", "hr_workforce", "clinical_epcr",
            "hipaa_compliance", "billing_rcm", "contracts", "medical_direction",
            "fleet_equipment", "accreditation", "insurance", "intellectual_prop",
        }
        if v not in known:
            raise ValueError(f"Unknown vault_id: {v!r}")
        return v


class DocumentUploadInitResponse(BaseModel):
    """Contains presigned POST fields for direct browser-to-S3 upload."""
    document_id: uuid.UUID
    presigned_url: str
    presigned_fields: dict[str, str]
    s3_bucket: str
    s3_key: str
    expires_in_seconds: int


class DocumentUploadConfirmRequest(BaseModel):
    """Called after the S3 upload completes to trigger OCR + classification."""
    document_id: uuid.UUID
    s3_version_id: str | None = None
    checksum_sha256: str | None = None
    file_size_bytes: int | None = None


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=512)
    doc_metadata: dict[str, Any] | None = None


class LockStateUpdateRequest(BaseModel):
    lock_state: str = Field(..., description="Target lock state")
    reason: str = Field(..., min_length=1, max_length=1024)

    @field_validator("lock_state")
    @classmethod
    def must_be_valid(cls, v: str) -> str:
        valid = {
            "active", "archived", "legal_hold", "tax_hold",
            "compliance_hold", "pending_disposition", "destroyed", "destroy_blocked",
        }
        if v not in valid:
            raise ValueError(f"Invalid lock state: {v!r}")
        return v


class AddendumAppendRequest(BaseModel):
    addendum_data: dict[str, Any]
    reason: str = Field(..., min_length=1, max_length=1024)


class PresignedDownloadResponse(BaseModel):
    document_id: uuid.UUID
    presigned_url: str
    expires_in_seconds: int


# ---------------------------------------------------------------------------
# Smart folder
# ---------------------------------------------------------------------------

class SmartFolderCreateRequest(BaseModel):
    vault_id: str
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    color: str | None = None
    icon_key: str | None = None
    document_ids: list[uuid.UUID] = Field(default_factory=list)


class SmartFolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vault_id: str
    name: str
    description: str | None
    color: str | None
    icon_key: str | None
    is_ai_generated: bool
    document_ids: list[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# Export package
# ---------------------------------------------------------------------------

class ExportPackageCreateRequest(BaseModel):
    package_name: str = Field(..., min_length=1, max_length=512)
    export_reason: str = Field(..., min_length=1, max_length=2048)
    document_ids: list[uuid.UUID] = Field(..., min_length=1)


class ExportPackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    package_name: str
    export_reason: str
    status: str
    document_count: int
    total_bytes: int
    expires_at: datetime | None
    s3_key: str | None
    error_detail: str | None
    created_at: datetime


class ExportPackageDownloadResponse(BaseModel):
    package_id: uuid.UUID
    presigned_url: str
    expires_in_seconds: int


# ---------------------------------------------------------------------------
# Retention policy
# ---------------------------------------------------------------------------

class RetentionPolicyUpdateRequest(BaseModel):
    vault_id: str
    retention_years: int | None = Field(None, gt=0)
    retention_days: int | None = Field(None, gt=0)
    is_permanent: bool = False
    notes: str | None = None


class RetentionPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vault_id: str
    retention_years: int | None
    retention_days: int | None
    is_permanent: bool
    notes: str | None
    updated_at: datetime


# ---------------------------------------------------------------------------
# Audit entries
# ---------------------------------------------------------------------------

class VaultAuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vault_id: str
    action: str
    actor_display: str | None
    occurred_at: datetime
    detail: dict[str, Any] | None


# ---------------------------------------------------------------------------
# Vault tree (composite response for the sidebar)
# ---------------------------------------------------------------------------

class VaultTreeResponse(BaseModel):
    vaults: list[VaultDefinitionOut]
    total_documents: int
    documents_on_hold: int


# ---------------------------------------------------------------------------
# AI classification result
# ---------------------------------------------------------------------------

class AIClassificationOut(BaseModel):
    document_id: uuid.UUID
    ai_document_type: str | None
    ai_tags: list[str] | None
    ai_summary: str | None
    ai_confidence: float | None
    ai_classification_status: str
    ai_classified_at: datetime | None
