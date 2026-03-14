"""
Document Vault ORM Models

Represents the Founder-Only Document Manager and Records Control System.
12 distinct vaults with Wisconsin retention law compliance, S3-backed storage,
KMS encryption references, AI/OCR classification, lock states, and full audit trails.

Vaults:
  1  legal_corporate    – Articles of incorporation, bylaws, equity, operating agreements
  2  tax_financial      – Tax returns, W-2s, 1099s, financial statements
  3  hr_workforce       – Employment records, I-9s, credentialing, background checks
  4  clinical_epcr      – Patient care reports, clinical documentation
  5  hipaa_compliance   – BAAs, privacy notices, HIPAA training, risk assessments
  6  billing_rcm        – CMS-1500s, EOBs, remittances, appeals, authorizations
  7  contracts          – Vendor contracts, agency agreements, NDAs, service agreements
  8  medical_direction  – Medical director agreements, protocols, standing orders
  9  fleet_equipment    – Vehicle titles, maintenance, equipment certs, inspections
  10 accreditation      – CAAS/CASC, QA/QI reports, accreditation certificates
  11 insurance          – Liability, workers comp, vehicle insurance, COIs
  12 intellectual_prop  – Patents, trademarks, trade secrets, product documentation
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class VaultId(enum.StrEnum):
    LEGAL_CORPORATE = "legal_corporate"
    TAX_FINANCIAL = "tax_financial"
    HR_WORKFORCE = "hr_workforce"
    CLINICAL_EPCR = "clinical_epcr"
    HIPAA_COMPLIANCE = "hipaa_compliance"
    BILLING_RCM = "billing_rcm"
    CONTRACTS = "contracts"
    MEDICAL_DIRECTION = "medical_direction"
    FLEET_EQUIPMENT = "fleet_equipment"
    ACCREDITATION = "accreditation"
    INSURANCE = "insurance"
    INTELLECTUAL_PROP = "intellectual_prop"


class DocumentLockState(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    LEGAL_HOLD = "legal_hold"
    TAX_HOLD = "tax_hold"
    COMPLIANCE_HOLD = "compliance_hold"
    PENDING_DISPOSITION = "pending_disposition"
    DESTROYED = "destroyed"
    DESTROY_BLOCKED = "destroy_blocked"


class ClassificationStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    CLASSIFIED = "classified"
    FAILED = "failed"


class ExportPackageStatus(enum.StrEnum):
    PENDING = "pending"
    BUILDING = "building"
    READY = "ready"
    EXPIRED = "expired"
    FAILED = "failed"


class AuditAction(enum.StrEnum):
    UPLOAD = "upload"
    DOWNLOAD = "download"
    VIEW = "view"
    LOCK_STATE_CHANGE = "lock_state_change"
    DELETE = "delete"
    OCR_COMPLETE = "ocr_complete"
    AI_CLASSIFY = "ai_classify"
    PACKAGE_EXPORT = "package_export"
    RETENTION_APPLIED = "retention_applied"
    ADDENDUM_APPEND = "addendum_append"
    METADATA_UPDATE = "metadata_update"
    SMART_FOLDER_ADD = "smart_folder_add"


# ---------------------------------------------------------------------------
# VaultDefinition  (static catalog — seeded once, not mutated at runtime)
# ---------------------------------------------------------------------------

class VaultDefinition(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Catalog record for each of the 12 document vaults.
    Seeded on first migration; not mutated at runtime.
    """
    __tablename__ = "vault_definitions"

    vault_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True,
        comment="Canonical vault identifier (VaultId enum value)"
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    s3_prefix: Mapped[str] = mapped_column(
        String(256), nullable=False,
        comment="S3 key prefix for all documents in this vault, e.g. 'vaults/legal_corporate/'"
    )
    retention_class: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="References WISCONSIN_DEFAULTS classes key"
    )
    retention_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_permanent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_legal_hold_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    icon_key: Mapped[str] = mapped_column(String(64), nullable=False, default="folder")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    documents: Mapped[list[DocumentRecord]] = relationship(
        "DocumentRecord",
        back_populates="vault",
        foreign_keys="DocumentRecord.vault_id",
        lazy="noload",
    )
    smart_folders: Mapped[list[SmartFolder]] = relationship(
        "SmartFolder", back_populates="vault", lazy="noload"
    )

    __table_args__ = (
        Index("ix_vaultdef_vault_id", "vault_id"),
    )


# ---------------------------------------------------------------------------
# DocumentRecord
# ---------------------------------------------------------------------------

class DocumentRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """
    Core document record.  Each file ingested into the vault creates one
    DocumentRecord.  S3 object reference, retention metadata, OCR text,
    and AI classification are stored here.
    """
    __tablename__ = "vault_documents"

    vault_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("vault_definitions.vault_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # S3 storage
    s3_bucket: Mapped[str] = mapped_column(String(256), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    s3_version_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Lock / retention
    lock_state: Mapped[str] = mapped_column(
        String(64), nullable=False, default=DocumentLockState.ACTIVE.value, index=True
    )
    retention_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retain_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposition_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # OCR / AI
    ocr_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ClassificationStatus.PENDING.value
    )
    ocr_job_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_classification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ClassificationStatus.PENDING.value
    )
    ai_document_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ai_tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)
    ai_classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata + addenda (JSONB)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment="Structured metadata: author, agency_id, case_number, effective_date, etc."
    )
    addenda: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list,
        comment="Append-only array of addendum records with timestamp and reason"
    )
    lock_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list,
        comment="Ordered history of lock state transitions with actor and reason"
    )

    # Actor tracking
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    uploaded_by_display: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Relationships
    vault: Mapped[VaultDefinition] = relationship(
        "VaultDefinition",
        back_populates="documents",
        foreign_keys=[vault_id],
    )
    versions: Mapped[list[DocumentVersion]] = relationship(
        "DocumentVersion", back_populates="document", lazy="noload",
        cascade="all, delete-orphan",
    )
    audit_entries: Mapped[list[VaultAuditEntry]] = relationship(
        "VaultAuditEntry", back_populates="document", lazy="noload",
        cascade="all, delete-orphan",
    )
    package_items: Mapped[list[PackageManifestItem]] = relationship(
        "PackageManifestItem", back_populates="document", lazy="noload",
    )

    __table_args__ = (
        Index("ix_vaultdoc_vault_lock", "vault_id", "lock_state"),
        Index("ix_vaultdoc_s3_key", "s3_key"),
        Index("ix_vaultdoc_ocr_status", "ocr_status"),
        Index("ix_vaultdoc_ai_status", "ai_classification_status"),
        Index("ix_vaultdoc_retain_until", "retain_until"),
    )


# ---------------------------------------------------------------------------
# DocumentVersion  (S3 versioned copies)
# ---------------------------------------------------------------------------

class DocumentVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable version record for each document upload/replacement.
    Points to a specific S3 version.
    """
    __tablename__ = "vault_document_versions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(256), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    s3_version_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped[DocumentRecord] = relationship("DocumentRecord", back_populates="versions")


# ---------------------------------------------------------------------------
# SmartFolder  (user-defined cross-vault groupings)
# ---------------------------------------------------------------------------

class SmartFolder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Named collection of documents within a vault.
    Supports manual pinning and AI-suggested groupings.
    """
    __tablename__ = "vault_smart_folders"

    vault_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("vault_definitions.vault_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)
    icon_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    document_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list,
        comment="Array of vault_documents.id UUIDs (as strings)"
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    vault: Mapped[VaultDefinition] = relationship("VaultDefinition", back_populates="smart_folders")

    __table_args__ = (
        Index("ix_smartfolder_vault", "vault_id"),
    )


# ---------------------------------------------------------------------------
# ExportPackage
# ---------------------------------------------------------------------------

class ExportPackage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Manifest for a ZIP export bundle.
    Records are created immediately; the S3 ZIP is built asynchronously.
    """
    __tablename__ = "vault_export_packages"

    package_name: Mapped[str] = mapped_column(String(512), nullable=False)
    export_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ExportPackageStatus.PENDING.value, index=True
    )
    s3_bucket: Mapped[str | None] = mapped_column(String(256), nullable=True)
    s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    items: Mapped[list[PackageManifestItem]] = relationship(
        "PackageManifestItem", back_populates="package",
        cascade="all, delete-orphan", lazy="noload",
    )

    __table_args__ = (
        Index("ix_exportpkg_status", "status"),
    )


# ---------------------------------------------------------------------------
# PackageManifestItem
# ---------------------------------------------------------------------------

class PackageManifestItem(Base, UUIDPrimaryKeyMixin):
    """Junction between ExportPackage and DocumentRecord."""
    __tablename__ = "vault_package_manifest_items"

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault_export_packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault_documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    path_in_zip: Mapped[str] = mapped_column(String(512), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(256), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    package: Mapped[ExportPackage] = relationship(
        "core_app.models.document_vault.ExportPackage", back_populates="items"
    )
    document: Mapped[DocumentRecord] = relationship("DocumentRecord", back_populates="package_items")


# ---------------------------------------------------------------------------
# VaultAuditEntry  (append-only)
# ---------------------------------------------------------------------------

class VaultAuditEntry(Base, UUIDPrimaryKeyMixin):
    """
    Append-only audit log for every significant action on a document.
    Never updated or deleted.
    """
    __tablename__ = "vault_audit_entries"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vault_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vault_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_display: Mapped[str | None] = mapped_column(String(256), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    document: Mapped[DocumentRecord] = relationship("DocumentRecord", back_populates="audit_entries")

    __table_args__ = (
        Index("ix_vaultaudit_doc_action", "document_id", "action"),
        Index("ix_vaultaudit_occurred_at", "occurred_at"),
    )


# ---------------------------------------------------------------------------
# VaultRetentionPolicy  (per-vault overrides beyond Wisconsin defaults)
# ---------------------------------------------------------------------------

class VaultRetentionPolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Operator-configurable retention overrides for a vault.
    Wisconsin defaults apply when no override exists.
    """
    __tablename__ = "vault_retention_policies"

    vault_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("vault_definitions.vault_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    retention_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_permanent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
