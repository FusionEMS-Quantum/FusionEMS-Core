"""SQLAlchemy models for the export / offboarding package system."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ExportPackage(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A requested export bundle (may be part of an offboarding or standalone)."""

    __tablename__ = "export_packages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True,
    )
    offboarding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offboarding_requests.id"), nullable=True,
    )

    # State machine
    state: Mapped[str] = mapped_column(String(32), default="REQUESTED", nullable=False, index=True)

    # Scope
    modules: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    date_range_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_range_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    patient_scope: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    account_scope: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    # Options
    include_attachments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    include_field_crosswalk: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Delivery
    delivery_method: Mapped[str] = mapped_column(String(32), default="SECURE_LINK", nullable=False)
    delivery_target: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Approval
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Package artifact
    package_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    manifest: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    integrity_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Secure link
    secure_link_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    secure_link_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    secure_link_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Risk
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_details: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class OffboardingRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Top-level offboarding request that may contain multiple export packages."""

    __tablename__ = "offboarding_requests"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True,
    )
    state: Mapped[str] = mapped_column(String(32), default="REQUESTED", nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    target_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_completion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_method: Mapped[str] = mapped_column(String(32), default="SECURE_LINK", nullable=False)
    delivery_target: Mapped[str | None] = mapped_column(String(512), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Risk
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_details: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExportAccessLog(Base, UUIDPrimaryKeyMixin):
    """Immutable access log for every export package interaction."""

    __tablename__ = "export_access_logs"

    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("export_packages.id"), nullable=False, index=True,
    )
    accessed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    access_type: Mapped[str] = mapped_column(String(32), nullable=False)  # DOWNLOAD, VIEW, REVOKE, REISSUE
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )


class ThirdPartyBiller(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Registry of authorized third-party billing entities for a tenant."""

    __tablename__ = "third_party_billers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True,
    )
    biller_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    portal_access_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    access_role: Mapped[str] = mapped_column(String(32), default="billing", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
