from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin


class ConnectorInstallState(enum.StrEnum):
    DISCOVERED = "DISCOVERED"
    CONFIG_PENDING = "CONFIG_PENDING"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    DISABLED = "DISABLED"


class SyncJobState(enum.StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WebhookDeliveryState(enum.StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    RETRYING = "RETRYING"
    DEAD_LETTERED = "DEAD_LETTERED"


class APIKeyState(enum.StrEnum):
    ACTIVE = "ACTIVE"
    ROTATING = "ROTATING"
    REVOKED = "REVOKED"


class ConnectorCatalog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "connector_catalog"

    connector_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    capabilities: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    auth_modes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    enabled_by_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ConnectorProfile(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "connector_profiles"

    connector_catalog_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_catalog.id"), nullable=False, index=True)
    profile_name: Mapped[str] = mapped_column(String(255), nullable=False)
    install_state: Mapped[ConnectorInstallState] = mapped_column(Enum(ConnectorInstallState), nullable=False, default=ConnectorInstallState.CONFIG_PENDING)
    endpoint_base_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    config_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    validation_report: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantConnectorInstall(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "tenant_connector_installs"

    connector_profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_profiles.id"), nullable=False, index=True)
    install_state: Mapped[ConnectorInstallState] = mapped_column(Enum(ConnectorInstallState), nullable=False, default=ConnectorInstallState.CONFIG_PENDING)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConnectorSecretMaterialization(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "connector_secret_materializations"

    tenant_connector_install_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_connector_installs.id"),
        nullable=False,
        index=True,
    )
    secret_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    materialized_by: Mapped[str] = mapped_column(String(128), nullable=False, default="oidc-runtime")
    materialized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConnectorSyncJob(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "connector_sync_jobs"

    tenant_connector_install_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_connector_installs.id"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[SyncJobState] = mapped_column(Enum(SyncJobState), nullable=False, default=SyncJobState.QUEUED)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class SyncDeadLetter(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "sync_dead_letters"

    connector_sync_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_sync_jobs.id"), nullable=False, index=True)
    external_record_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class ConnectorWebhookEndpoint(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "connector_webhook_endpoints"

    tenant_connector_install_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_connector_installs.id"),
        nullable=False,
        index=True,
    )
    endpoint_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    signing_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="hmac-sha256")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ConnectorWebhookDelivery(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "connector_webhook_deliveries"

    connector_webhook_endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("connector_webhook_endpoints.id"),
        nullable=False,
        index=True,
    )
    state: Mapped[WebhookDeliveryState] = mapped_column(Enum(WebhookDeliveryState), nullable=False, default=WebhookDeliveryState.PENDING)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class APIClientCredential(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "api_client_credentials"

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    credential_state: Mapped[APIKeyState] = mapped_column(Enum(APIKeyState), nullable=False, default=APIKeyState.ACTIVE)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class APIClientQuota(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "api_client_quotas"

    api_client_credential_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_client_credentials.id"), nullable=False, index=True)
    requests_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=600)
    requests_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=250000)
    burst_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=1200)


class APIClientUsageWindow(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "api_client_usage_windows"

    api_client_credential_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_client_credentials.id"), nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    denied_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class IntegrationAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "integration_audit_events"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
