from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin


class RecordLifecycleState(enum.StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    SEALED = "SEALED"
    LOCKED = "LOCKED"
    RELEASED = "RELEASED"


class SignatureState(enum.StrEnum):
    MISSING = "MISSING"
    CAPTURED = "CAPTURED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class OCRConfidenceBand(enum.StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ChainOfCustodyState(enum.StrEnum):
    CLEAN = "CLEAN"
    ANOMALY = "ANOMALY"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class ExportDeliveryState(enum.StrEnum):
    QUEUED = "QUEUED"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class QAExceptionState(enum.StrEnum):
    OPEN = "OPEN"
    REMEDIATED = "REMEDIATED"
    ESCALATED = "ESCALATED"


class ClinicalRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "clinical_records"

    incident_number: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    patient_external_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lifecycle_state: Mapped[RecordLifecycleState] = mapped_column(Enum(RecordLifecycleState), nullable=False, default=RecordLifecycleState.DRAFT)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecordSection(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "record_sections"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    section_type: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    hash_sha256: Mapped[str] = mapped_column(String(128), nullable=False)


class DocumentArtifact(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "document_artifacts"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(128), nullable=False)


class SignatureCapture(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "signature_captures"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    signer_role: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_state: Mapped[SignatureState] = mapped_column(Enum(SignatureState), nullable=False, default=SignatureState.MISSING)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class OCRProcessingResult(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ocr_processing_results"

    document_artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_artifacts.id"), nullable=False, index=True)
    engine: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence_band: Mapped[OCRConfidenceBand] = mapped_column(Enum(OCRConfidenceBand), nullable=False, default=OCRConfidenceBand.MEDIUM)
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    extraction_warnings: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class ChainOfCustodyEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "chain_of_custody_events"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    state: Mapped[ChainOfCustodyState] = mapped_column(Enum(ChainOfCustodyState), nullable=False, default=ChainOfCustodyState.CLEAN)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CompliancePacket(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "compliance_packets"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    packet_type: Mapped[str] = mapped_column(String(128), nullable=False)
    packet_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rendered_artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_artifacts.id"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LegalHold(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "legal_holds"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    hold_owner: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReleaseAuthorization(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "release_authorizations"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    requestor: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecordExport(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "record_exports"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    destination_system: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[ExportDeliveryState] = mapped_column(Enum(ExportDeliveryState), nullable=False, default=ExportDeliveryState.QUEUED)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class QAException(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "qa_exceptions"

    clinical_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clinical_records.id"), nullable=False, index=True)
    rule_code: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[QAExceptionState] = mapped_column(Enum(QAExceptionState), nullable=False, default=QAExceptionState.OPEN)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    remediated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecordsAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "records_audit_events"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
