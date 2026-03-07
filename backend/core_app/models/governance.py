import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin

# --- Authentication ---

class UserStatus(enum.StrEnum):
    INVITED = "invited"
    ACTIVATION_PENDING = "activation_pending"
    ACTIVE = "active"
    MFA_REQUIRED = "mfa_required"
    LOCKED = "locked"
    DISABLED = "disabled"
    PASSWORD_RESET_PENDING = "password_reset_pending"
    SESSION_EXPIRED = "session_expired"

class AuthenticationEventType(enum.StrEnum):
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    MFA_CHALLENGE = "mfa_challenge"
    MFA_VERIFIED = "mfa_verified"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"
    INVITE_SENT = "invite_sent"
    INVITE_ACCEPTED = "invite_accepted"
    SESSION_EXPIRED = "session_expired"

class AuthenticationEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "auth_events"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type: Mapped[AuthenticationEventType] = mapped_column(Enum(AuthenticationEventType), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class UserSession(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "user_sessions"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class SupportAccessGrant(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "support_access_grants"
    
    granted_to_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# --- Authorization ---

class Permission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "permissions"
    
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

class RolePermission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "role_permissions"
    
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)

class ProtectedActionStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"

class ProtectedActionApproval(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "protected_action_approvals"
    
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[ProtectedActionStatus] = mapped_column(Enum(ProtectedActionStatus), default=ProtectedActionStatus.PENDING, nullable=False)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

# --- PHI & Sensitive Data ---

class PhiaAccessAudit(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "phi_access_audits"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False) # e.g., "Patient", "Incident"
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    access_type: Mapped[str] = mapped_column(String(32), nullable=False) # "VIEW", "EXPORT", "EDIT"
    fields_accessed: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DataExportRequest(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "data_export_requests"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    export_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

# --- Interoperability ---

class DataProvenance(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "data_provenance"
    
    entity_name: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True, default=dict)

class HandoffExchangeRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "handoff_exchange_records"
    
    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    destination_facility: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange_type: Mapped[str] = mapped_column(String(64), nullable=False) # e.g., "FHIR_BUNDLE", "PDF_DOCUMENT"
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)

# --- Policy ---

class TenantPolicy(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, VersionMixin):
    __tablename__ = "tenant_policies"
    
    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
