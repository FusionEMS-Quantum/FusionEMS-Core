"""Security directive completion — all remaining governance tables

Revision ID: 20260309_0033
Revises: e294733db472
Create Date: 2026-03-09

Adds all tables and columns introduced by the 13-part
MASTER SECURITY + COMPLIANCE + AUDIT + INTEROPERABILITY BUILD DIRECTIVE
that were not yet covered by migration e294733db472.

New tables
----------
  Part 1 (Auth):
    user_invites
    password_reset_tokens

  Part 2 (AuthZ / RBAC):
    user_role_assignments
    tenant_scope_rules
    authorization_audit_events

  Part 3 (Audit):
    audit_correlations
    audit_snapshots
    audit_retention_policies

  Part 4 (PHI):
    sensitive_field_policies
    sensitive_document_accesses
    attachment_access_events
    export_audit_events

  Part 5 (Interop):
    external_identifiers
    interop_mapping_rules
    interop_payloads
    interop_import_records
    interop_export_records

  Part 6 (Policy):
    policy_versions
    policy_approvals
    policy_change_audit_events

Column additions to existing tables
-------------------------------------
  user_sessions     : revoked_reason, ip_address, device_fingerprint
  phi_access_audits : access_state
  data_export_requests : approval_reason, record_count, is_encrypted, recipient_email
  handoff_exchange_records : acknowledged_at, acknowledged_by
  roles             : parent_role_id, is_system
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260309_0033"
down_revision: str = "e294733db472"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────────────────
# Idempotency helpers
# ─────────────────────────────────────────────────────────────────────────────


def _table_exists(conn: sa.engine.Connection, table: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    )
    return result.first() is not None


def _column_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return result.first() is not None


# ─────────────────────────────────────────────────────────────────────────────
# Upgrade
# ─────────────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    conn = op.get_bind()

    # ── Column additions to existing tables ─────────────────────────────────

    if not _column_exists(conn, "user_sessions", "revoked_reason"):
        op.add_column("user_sessions", sa.Column("revoked_reason", sa.String(128), nullable=True))

    if not _column_exists(conn, "user_sessions", "ip_address"):
        op.add_column("user_sessions", sa.Column("ip_address", sa.String(45), nullable=True))

    if not _column_exists(conn, "user_sessions", "device_fingerprint"):
        op.add_column("user_sessions", sa.Column("device_fingerprint", sa.String(255), nullable=True))

    if not _column_exists(conn, "phi_access_audits", "access_state"):
        op.add_column(
            "phi_access_audits",
            sa.Column(
                "access_state",
                sa.String(32),
                nullable=False,
                server_default="view_allowed",
            ),
        )

    if not _column_exists(conn, "data_export_requests", "approval_reason"):
        op.add_column("data_export_requests", sa.Column("approval_reason", sa.Text(), nullable=True))

    if not _column_exists(conn, "data_export_requests", "record_count"):
        op.add_column("data_export_requests", sa.Column("record_count", sa.Integer(), nullable=True))

    if not _column_exists(conn, "data_export_requests", "is_encrypted"):
        op.add_column(
            "data_export_requests",
            sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    if not _column_exists(conn, "data_export_requests", "recipient_email"):
        op.add_column("data_export_requests", sa.Column("recipient_email", sa.String(320), nullable=True))

    if not _column_exists(conn, "handoff_exchange_records", "acknowledged_at"):
        op.add_column(
            "handoff_exchange_records",
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists(conn, "handoff_exchange_records", "acknowledged_by"):
        op.add_column("handoff_exchange_records", sa.Column("acknowledged_by", sa.String(255), nullable=True))

    if not _column_exists(conn, "roles", "parent_role_id"):
        op.add_column(
            "roles",
            sa.Column(
                "parent_role_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("roles.id"),
                nullable=True,
            ),
        )

    if not _column_exists(conn, "roles", "is_system"):
        op.add_column(
            "roles",
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    # ── PART 1: user_invites ─────────────────────────────────────────────────

    if not _table_exists(conn, "user_invites"):
        op.create_table(
            "user_invites",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_user_invites_tenant_id", "user_invites", ["tenant_id"])
        op.create_index("ix_user_invites_email", "user_invites", ["email"])

    # ── PART 1: password_reset_tokens ────────────────────────────────────────

    if not _table_exists(conn, "password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_consumed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_password_reset_tokens_tenant_id", "password_reset_tokens", ["tenant_id"])
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    # ── PART 2: user_role_assignments ────────────────────────────────────────

    if not _table_exists(conn, "user_role_assignments"):
        op.create_table(
            "user_role_assignments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
            sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_user_role_tenant"),
        )
        op.create_index("ix_user_role_assignments_tenant_id", "user_role_assignments", ["tenant_id"])
        op.create_index("ix_user_role_assignments_user", "user_role_assignments", ["user_id"])

    # ── PART 2: tenant_scope_rules ───────────────────────────────────────────

    if not _table_exists(conn, "tenant_scope_rules"):
        op.create_table(
            "tenant_scope_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("resource_type", sa.String(64), nullable=False),
            sa.Column("allowed_actions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("condition_expression", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_tenant_scope_rules_tenant_id", "tenant_scope_rules", ["tenant_id"])

    # ── PART 2: authorization_audit_events ───────────────────────────────────

    if not _table_exists(conn, "authorization_audit_events"):
        op.create_table(
            "authorization_audit_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("action", sa.String(128), nullable=False),
            sa.Column("resource_type", sa.String(64), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("decision", sa.String(16), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_authorization_audit_events_tenant_id", "authorization_audit_events", ["tenant_id"])
        op.create_index("ix_authorization_audit_events_user", "authorization_audit_events", ["user_id"])

    # ── PART 3: audit_correlations ───────────────────────────────────────────

    if not _table_exists(conn, "audit_correlations"):
        op.create_table(
            "audit_correlations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("correlation_id", sa.String(64), nullable=False),
            sa.Column("audit_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("audit_logs.id"), nullable=False),
            sa.Column("domain", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_audit_correlations_tenant_id", "audit_correlations", ["tenant_id"])
        op.create_index("ix_audit_correlation_cid", "audit_correlations", ["correlation_id"])

    # ── PART 3: audit_snapshots ──────────────────────────────────────────────

    if not _table_exists(conn, "audit_snapshots"):
        op.create_table(
            "audit_snapshots",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("snapshot_type", sa.String(64), nullable=False),
            sa.Column("entity_name", sa.String(128), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("snapshot_data", sa.JSON(), nullable=False),
            sa.Column("captured_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_audit_snapshots_tenant_id", "audit_snapshots", ["tenant_id"])

    # ── PART 3: audit_retention_policies ────────────────────────────────────

    if not _table_exists(conn, "audit_retention_policies"):
        op.create_table(
            "audit_retention_policies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("domain", sa.String(64), nullable=False),
            sa.Column("retention_days", sa.Integer(), nullable=False, server_default="2555"),
            sa.Column("archive_after_days", sa.Integer(), nullable=False, server_default="365"),
            sa.Column("is_regulatory_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("hold_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "domain", name="uq_retention_tenant_domain"),
        )
        op.create_index("ix_audit_retention_policies_tenant_id", "audit_retention_policies", ["tenant_id"])

    # ── PART 4: sensitive_field_policies ────────────────────────────────────

    if not _table_exists(conn, "sensitive_field_policies"):
        op.create_table(
            "sensitive_field_policies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("resource_type", sa.String(64), nullable=False),
            sa.Column("field_name", sa.String(64), nullable=False),
            sa.Column("default_state", sa.String(32), nullable=False, server_default="masked"),
            sa.Column("allowed_roles", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("context_conditions", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "resource_type", "field_name", name="uq_sensitive_field_policy"),
        )
        op.create_index("ix_sensitive_field_policies_tenant_id", "sensitive_field_policies", ["tenant_id"])

    # ── PART 4: sensitive_document_accesses ──────────────────────────────────

    if not _table_exists(conn, "sensitive_document_accesses"):
        op.create_table(
            "sensitive_document_accesses",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("document_type", sa.String(64), nullable=False),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("access_action", sa.String(32), nullable=False),
            sa.Column("access_state", sa.String(32), nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_sensitive_document_accesses_tenant_id", "sensitive_document_accesses", ["tenant_id"])
        op.create_index("ix_sensitive_document_accesses_user", "sensitive_document_accesses", ["user_id"])

    # ── PART 4: attachment_access_events ────────────────────────────────────

    if not _table_exists(conn, "attachment_access_events"):
        op.create_table(
            "attachment_access_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("action", sa.String(32), nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_attachment_access_events_tenant_id", "attachment_access_events", ["tenant_id"])

    # ── PART 4: export_audit_events ──────────────────────────────────────────

    if not _table_exists(conn, "export_audit_events"):
        op.create_table(
            "export_audit_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "export_request_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("data_export_requests.id"),
                nullable=False,
            ),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_export_audit_events_tenant_id", "export_audit_events", ["tenant_id"])
        op.create_index("ix_export_audit_events_request", "export_audit_events", ["export_request_id"])

    # ── PART 5: external_identifiers ────────────────────────────────────────

    if not _table_exists(conn, "external_identifiers"):
        op.create_table(
            "external_identifiers",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("entity_type", sa.String(64), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("system_uri", sa.String(255), nullable=False),
            sa.Column("identifier_value", sa.String(255), nullable=False),
            sa.Column("identifier_type", sa.String(64), nullable=True),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("tenant_id", "system_uri", "identifier_value", name="uq_external_identifier"),
        )
        op.create_index("ix_external_identifiers_tenant_id", "external_identifiers", ["tenant_id"])
        op.create_index("ix_ext_id_entity", "external_identifiers", ["entity_type", "entity_id"])

    # ── PART 5: interop_mapping_rules ────────────────────────────────────────

    if not _table_exists(conn, "interop_mapping_rules"):
        op.create_table(
            "interop_mapping_rules",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_system", sa.String(128), nullable=False),
            sa.Column("source_field", sa.String(128), nullable=False),
            sa.Column("target_entity", sa.String(128), nullable=False),
            sa.Column("target_field", sa.String(128), nullable=False),
            sa.Column("transform_expression", sa.Text(), nullable=True),
            sa.Column("default_value", sa.String(255), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_interop_mapping_rules_tenant_id", "interop_mapping_rules", ["tenant_id"])
        op.create_index("ix_interop_mapping_source", "interop_mapping_rules", ["source_system", "source_field"])

    # ── PART 5: interop_payloads ─────────────────────────────────────────────

    if not _table_exists(conn, "interop_payloads"):
        op.create_table(
            "interop_payloads",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_system", sa.String(128), nullable=False),
            sa.Column("payload_type", sa.String(64), nullable=False),
            sa.Column("schema_version", sa.String(32), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="received"),
            sa.Column("validation_errors", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_interop_payloads_tenant_id", "interop_payloads", ["tenant_id"])

    # ── PART 5: interop_import_records ───────────────────────────────────────

    if not _table_exists(conn, "interop_import_records"):
        op.create_table(
            "interop_import_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "payload_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("interop_payloads.id"),
                nullable=False,
            ),
            sa.Column("source_system", sa.String(128), nullable=False),
            sa.Column("entity_type", sa.String(64), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("field_mapping_used", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
            sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_interop_import_records_tenant_id", "interop_import_records", ["tenant_id"])

    # ── PART 5: interop_export_records ───────────────────────────────────────

    if not _table_exists(conn, "interop_export_records"):
        op.create_table(
            "interop_export_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("entity_type", sa.String(64), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("destination_system", sa.String(128), nullable=False),
            sa.Column("export_format", sa.String(32), nullable=False),
            sa.Column("payload_reference", sa.String(512), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_interop_export_records_tenant_id", "interop_export_records", ["tenant_id"])

    # ── PART 6: policy_versions ──────────────────────────────────────────────

    if not _table_exists(conn, "policy_versions"):
        op.create_table(
            "policy_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "policy_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenant_policies.id"),
                nullable=False,
            ),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("value_snapshot", sa.JSON(), nullable=False),
            sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("change_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("policy_id", "version_number", name="uq_policy_version"),
        )
        op.create_index("ix_policy_versions_tenant_id", "policy_versions", ["tenant_id"])
        op.create_index("ix_policy_versions_policy_id", "policy_versions", ["policy_id"])

    # ── PART 6: policy_approvals ─────────────────────────────────────────────

    if not _table_exists(conn, "policy_approvals"):
        op.create_table(
            "policy_approvals",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "policy_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenant_policies.id"),
                nullable=False,
            ),
            sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("proposed_value", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("review_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_policy_approvals_tenant_id", "policy_approvals", ["tenant_id"])
        op.create_index("ix_policy_approvals_policy_id", "policy_approvals", ["policy_id"])

    # ── PART 6: policy_change_audit_events ───────────────────────────────────

    if not _table_exists(conn, "policy_change_audit_events"):
        op.create_table(
            "policy_change_audit_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "policy_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tenant_policies.id"),
                nullable=False,
            ),
            sa.Column("policy_key", sa.String(128), nullable=False),
            sa.Column("change_type", sa.String(32), nullable=False),
            sa.Column("old_value", sa.JSON(), nullable=True),
            sa.Column("new_value", sa.JSON(), nullable=False),
            sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_policy_change_audit_events_tenant_id", "policy_change_audit_events", ["tenant_id"])
        op.create_index("ix_policy_change_audit_policy", "policy_change_audit_events", ["policy_id"])


# ─────────────────────────────────────────────────────────────────────────────
# Downgrade — reverse in dependency order
# ─────────────────────────────────────────────────────────────────────────────


def downgrade() -> None:
    conn = op.get_bind()

    # Part 6
    if _table_exists(conn, "policy_change_audit_events"):
        op.drop_table("policy_change_audit_events")
    if _table_exists(conn, "policy_approvals"):
        op.drop_table("policy_approvals")
    if _table_exists(conn, "policy_versions"):
        op.drop_table("policy_versions")

    # Part 5
    if _table_exists(conn, "interop_export_records"):
        op.drop_table("interop_export_records")
    if _table_exists(conn, "interop_import_records"):
        op.drop_table("interop_import_records")
    if _table_exists(conn, "interop_payloads"):
        op.drop_table("interop_payloads")
    if _table_exists(conn, "interop_mapping_rules"):
        op.drop_table("interop_mapping_rules")
    if _table_exists(conn, "external_identifiers"):
        op.drop_table("external_identifiers")

    # Part 4
    if _table_exists(conn, "export_audit_events"):
        op.drop_table("export_audit_events")
    if _table_exists(conn, "attachment_access_events"):
        op.drop_table("attachment_access_events")
    if _table_exists(conn, "sensitive_document_accesses"):
        op.drop_table("sensitive_document_accesses")
    if _table_exists(conn, "sensitive_field_policies"):
        op.drop_table("sensitive_field_policies")

    # Part 3
    if _table_exists(conn, "audit_retention_policies"):
        op.drop_table("audit_retention_policies")
    if _table_exists(conn, "audit_snapshots"):
        op.drop_table("audit_snapshots")
    if _table_exists(conn, "audit_correlations"):
        op.drop_table("audit_correlations")

    # Part 2
    if _table_exists(conn, "authorization_audit_events"):
        op.drop_table("authorization_audit_events")
    if _table_exists(conn, "tenant_scope_rules"):
        op.drop_table("tenant_scope_rules")
    if _table_exists(conn, "user_role_assignments"):
        op.drop_table("user_role_assignments")

    # Part 1
    if _table_exists(conn, "password_reset_tokens"):
        op.drop_table("password_reset_tokens")
    if _table_exists(conn, "user_invites"):
        op.drop_table("user_invites")

    # Column removals from existing tables
    if _column_exists(conn, "roles", "is_system"):
        op.drop_column("roles", "is_system")
    if _column_exists(conn, "roles", "parent_role_id"):
        op.drop_column("roles", "parent_role_id")
    if _column_exists(conn, "handoff_exchange_records", "acknowledged_by"):
        op.drop_column("handoff_exchange_records", "acknowledged_by")
    if _column_exists(conn, "handoff_exchange_records", "acknowledged_at"):
        op.drop_column("handoff_exchange_records", "acknowledged_at")
    if _column_exists(conn, "data_export_requests", "recipient_email"):
        op.drop_column("data_export_requests", "recipient_email")
    if _column_exists(conn, "data_export_requests", "is_encrypted"):
        op.drop_column("data_export_requests", "is_encrypted")
    if _column_exists(conn, "data_export_requests", "record_count"):
        op.drop_column("data_export_requests", "record_count")
    if _column_exists(conn, "data_export_requests", "approval_reason"):
        op.drop_column("data_export_requests", "approval_reason")
    if _column_exists(conn, "phi_access_audits", "access_state"):
        op.drop_column("phi_access_audits", "access_state")
    if _column_exists(conn, "user_sessions", "device_fingerprint"):
        op.drop_column("user_sessions", "device_fingerprint")
    if _column_exists(conn, "user_sessions", "ip_address"):
        op.drop_column("user_sessions", "ip_address")
    if _column_exists(conn, "user_sessions", "revoked_reason"):
        op.drop_column("user_sessions", "revoked_reason")
