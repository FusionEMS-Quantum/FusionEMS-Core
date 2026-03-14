from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin


class TerminologyCodeSystem(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "terminology_code_systems"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "system_uri",
            "system_version",
            name="uq_term_code_systems_tenant_uri_version",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    # Canonical URI (FHIR CodeSystem.url compatible)
    system_uri: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Release/version label (e.g., "2026", "2025AA", "3.5.1").
    # NOTE: Uses a distinct column name to avoid clashing with VersionMixin.version.
    system_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    is_external: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    metadata_blob: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class TerminologyDatasetVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "terminology_dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code_system_id",
            "dataset_source",
            "source_version",
            name="uq_term_dataset_versions_tenant_system_source_ver",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    code_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terminology_code_systems.id"), nullable=False, index=True
    )

    dataset_source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    imported_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="imported")

    metadata_blob: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class TerminologyConcept(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "terminology_concepts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code_system_id",
            "code",
            name="uq_term_concepts_tenant_system_code",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    code_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terminology_code_systems.id"), nullable=False, index=True
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class TerminologySynonym(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "terminology_synonyms"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "concept_id",
            "synonym",
            name="uq_term_synonyms_tenant_concept_syn",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terminology_concepts.id"), nullable=False, index=True
    )

    synonym: Mapped[str] = mapped_column(String(512), nullable=False, index=True)


class TerminologyMapping(Base, UUIDPrimaryKeyMixin, TimestampMixin, VersionMixin):
    __tablename__ = "terminology_mappings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "from_concept_id",
            "to_concept_id",
            "map_type",
            "source",
            name="uq_term_mappings_tenant_from_to_type_source",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    from_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terminology_concepts.id"), nullable=False, index=True
    )
    to_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terminology_concepts.id"), nullable=False, index=True
    )

    map_type: Mapped[str] = mapped_column(String(32), nullable=False, default="equivalent")
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")

    confidence: Mapped[float | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    metadata_blob: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class TerminologyRefreshSchedule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "terminology_refresh_schedules"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "code_system_id",
            "schedule_key",
            name="uq_term_refresh_tenant_system_key",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    code_system_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terminology_code_systems.id"), nullable=False, index=True
    )

    schedule_key: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_source: Mapped[str] = mapped_column(String(64), nullable=False)

    # Simplest deterministic scheduling primitive: fixed interval in hours
    refresh_interval_hours: Mapped[int] = mapped_column(nullable=False, default=24)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    last_run_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_run_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_blob: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
