# pylint: disable=not-callable,unsubscriptable-object
import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, VersionMixin
from core_app.models.tenant import TenantScopedMixin

# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 — Authentication State Machine
# ═══════════════════════════════════════════════════════════════════════════════


class UserStatus(enum.StrEnum):
    INVITED = "invited"
    ACTIVATION_PENDING = "activation_pending"
    ACTIVE = "active"
    MFA_REQUIRED = "mfa_required"
    LOCKED = "locked"
    DISABLED = "disabled"
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"
    PASSWORD_RESET_PENDING = "password_reset_pending"
    SESSION_EXPIRED = "session_expired"


# Valid state transitions for the auth state machine enforcer
USER_STATUS_TRANSITIONS: dict[UserStatus, frozenset[UserStatus]] = {
    UserStatus.INVITED: frozenset({UserStatus.ACTIVATION_PENDING, UserStatus.DISABLED}),
    UserStatus.ACTIVATION_PENDING: frozenset({UserStatus.ACTIVE, UserStatus.DISABLED}),
    UserStatus.ACTIVE: frozenset(
        {UserStatus.LOCKED, UserStatus.DISABLED, UserStatus.DEACTIVATED, UserStatus.MFA_REQUIRED, UserStatus.PASSWORD_RESET_PENDING}
    ),
    UserStatus.MFA_REQUIRED: frozenset({UserStatus.ACTIVE, UserStatus.LOCKED}),
    UserStatus.LOCKED: frozenset({UserStatus.ACTIVE, UserStatus.DISABLED, UserStatus.DEACTIVATED}),
    UserStatus.DISABLED: frozenset({UserStatus.REACTIVATED}),
    UserStatus.DEACTIVATED: frozenset({UserStatus.REACTIVATED}),
    UserStatus.REACTIVATED: frozenset({UserStatus.ACTIVE, UserStatus.MFA_REQUIRED}),
    UserStatus.PASSWORD_RESET_PENDING: frozenset({UserStatus.ACTIVE, UserStatus.LOCKED}),
    UserStatus.SESSION_EXPIRED: frozenset({UserStatus.ACTIVE, UserStatus.MFA_REQUIRED}),
}


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
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_REACTIVATED = "account_reactivated"
    STATUS_TRANSITION = "status_transition"


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
    revoked_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)


class UserInvite(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "user_invites"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_consumed: Mapped[bool] = mapped_column(default=False, nullable=False)


class PasswordResetToken(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_consumed: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SupportAccessGrant(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "support_access_grants"

    granted_to_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 — Authorization & RBAC
# ═══════════════════════════════════════════════════════════════════════════════


class SystemRole(enum.StrEnum):
    FOUNDER = "founder"
    AGENCY_ADMIN = "agency_admin"
    BILLING = "billing"
    CLINICAL_PROVIDER = "clinical_provider"
    EMS = "ems"
    DISPATCHER = "dispatcher"
    COMPLIANCE = "compliance"
    SUPERVISOR = "supervisor"
    VIEWER = "viewer"


class Permission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)


class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parent_role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)


class RolePermission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False)

    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)


class TenantScopeRule(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "tenant_scope_rules"

    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed_actions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    condition_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class AuthorizationAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "authorization_audit_events"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)  # ALLOW or DENY
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3 — Audit & Traceability
# ═══════════════════════════════════════════════════════════════════════════════


class AuditEventDomain(enum.StrEnum):
    AUTH_EVENT = "auth_event"
    ACCESS_EVENT = "access_event"
    CLINICAL_EVENT = "clinical_event"
    BILLING_EVENT = "billing_event"
    PAYMENT_EVENT = "payment_event"
    COMMUNICATION_EVENT = "communication_event"
    PAGING_EVENT = "paging_event"
    SCHEDULING_EVENT = "scheduling_event"
    INVENTORY_EVENT = "inventory_event"
    NARCOTICS_EVENT = "narcotics_event"
    FLEET_EVENT = "fleet_event"
    EXPORT_EVENT = "export_event"
    DEPLOYMENT_EVENT = "deployment_event"
    POLICY_CHANGE_EVENT = "policy_change_event"


class AuditCorrelation(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "audit_correlations"

    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    audit_log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("audit_logs.id"), nullable=False)
    domain: Mapped[AuditEventDomain] = mapped_column(Enum(AuditEventDomain), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_audit_correlation_cid", "correlation_id"),)


class AuditSnapshot(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "audit_snapshots"

    snapshot_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    snapshot_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    captured_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditRetentionPolicy(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "audit_retention_policies"

    domain: Mapped[AuditEventDomain] = mapped_column(Enum(AuditEventDomain), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2555)  # ~7 years default
    archive_after_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    is_regulatory_hold: Mapped[bool] = mapped_column(default=False, nullable=False)
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "domain", name="uq_retention_tenant_domain"),)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 4 — PHI & Sensitive Data Controls
# ═══════════════════════════════════════════════════════════════════════════════


class PHIAccessState(enum.StrEnum):
    MASKED = "masked"
    VIEW_ALLOWED = "view_allowed"
    VIEW_BLOCKED = "view_blocked"
    EXPORT_ALLOWED = "export_allowed"
    EXPORT_BLOCKED = "export_blocked"
    REVIEW_REQUIRED = "review_required"


class PhiaAccessAudit(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "phi_access_audits"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    access_type: Mapped[str] = mapped_column(String(32), nullable=False)
    access_state: Mapped[PHIAccessState] = mapped_column(
        Enum(PHIAccessState), default=PHIAccessState.VIEW_ALLOWED, nullable=False
    )
    fields_accessed: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SensitiveFieldPolicy(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "sensitive_field_policies"

    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    default_state: Mapped[PHIAccessState] = mapped_column(Enum(PHIAccessState), default=PHIAccessState.MASKED, nullable=False)
    allowed_roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    context_conditions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "resource_type", "field_name", name="uq_sensitive_field_policy"),
    )


class SensitiveDocumentAccess(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "sensitive_document_accesses"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    access_action: Mapped[str] = mapped_column(String(32), nullable=False)  # VIEW, DOWNLOAD, PRINT
    access_state: Mapped[PHIAccessState] = mapped_column(Enum(PHIAccessState), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AttachmentAccessEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "attachment_access_events"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    attachment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # VIEW, DOWNLOAD, DELETE
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DataExportStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class DataExportRequest(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "data_export_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    export_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[DataExportStatus] = mapped_column(
        Enum(DataExportStatus), default=DataExportStatus.PENDING, nullable=False
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approval_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    record_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_encrypted: Mapped[bool] = mapped_column(default=False, nullable=False)
    recipient_email: Mapped[str | None] = mapped_column(String(320), nullable=True)


class ExportAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "export_audit_events"

    export_request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_export_requests.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # REQUESTED, APPROVED, DENIED, DOWNLOADED, EXPIRED
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 5 — Interoperability Readiness
# ═══════════════════════════════════════════════════════════════════════════════


class DataProvenance(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "data_provenance"

    entity_name: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=True, default=dict)


class ExternalIdentifier(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "external_identifiers"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    system_uri: Mapped[str] = mapped_column(String(255), nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(255), nullable=False)
    identifier_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "system_uri", "identifier_value", name="uq_external_identifier"),
        Index("ix_ext_id_entity", "entity_type", "entity_id"),
    )


class InteropMappingRule(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "interop_mapping_rules"

    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    source_field: Mapped[str] = mapped_column(String(128), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(128), nullable=False)
    target_field: Mapped[str] = mapped_column(String(128), nullable=False)
    transform_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        Index("ix_interop_mapping_source", "source_system", "source_field"),
    )


class InteropPayloadStatus(enum.StrEnum):
    RECEIVED = "received"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    TRANSFORMED = "transformed"
    IMPORTED = "imported"
    REJECTED = "rejected"


class InteropPayload(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "interop_payloads"

    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_type: Mapped[str] = mapped_column(String(64), nullable=False)  # FHIR_BUNDLE, HL7V2, CSV, CUSTOM
    schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[InteropPayloadStatus] = mapped_column(
        Enum(InteropPayloadStatus), default=InteropPayloadStatus.RECEIVED, nullable=False
    )
    validation_errors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InteropDirection(enum.StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class InteropImportRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "interop_import_records"

    payload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interop_payloads.id"), nullable=False)
    source_system: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # SUCCESS, PARTIAL, FAILED, DUPLICATE
    field_mapping_used: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class InteropExportRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "interop_export_records"

    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    destination_system: Mapped[str] = mapped_column(String(128), nullable=False)
    export_format: Mapped[str] = mapped_column(String(32), nullable=False)  # FHIR_R4, HL7V2, CDA, CSV
    payload_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # QUEUED, SENT, ACKNOWLEDGED, FAILED
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HandoffExchangeStatus(enum.StrEnum):
    CREATED = "created"
    PAYLOAD_GENERATED = "payload_generated"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    REJECTED = "rejected"


class HandoffExchangeRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "handoff_exchange_records"

    incident_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False)
    destination_facility: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[HandoffExchangeStatus] = mapped_column(
        Enum(HandoffExchangeStatus), default=HandoffExchangeStatus.CREATED, nullable=False
    )
    payload_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 6 — Policy & Configuration
# ═══════════════════════════════════════════════════════════════════════════════


class TenantPolicy(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin, VersionMixin):
    __tablename__ = "tenant_policies"

    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class PolicyVersion(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "policy_versions"

    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant_policies.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    value_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("policy_id", "version_number", name="uq_policy_version"),
    )


class PolicyApprovalStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"


class PolicyApproval(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "policy_approvals"

    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant_policies.id"), nullable=False)
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    proposed_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[PolicyApprovalStatus] = mapped_column(
        Enum(PolicyApprovalStatus), default=PolicyApprovalStatus.PENDING, nullable=False
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class PolicyChangeAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "policy_change_audit_events"

    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant_policies.id"), nullable=False)
    policy_key: Mapped[str] = mapped_column(String(128), nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)  # CREATE, UPDATE, DEACTIVATE, ROLLBACK
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
