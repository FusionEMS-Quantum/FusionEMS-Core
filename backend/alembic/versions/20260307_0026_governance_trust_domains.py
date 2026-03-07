"""Governance trust domain tables

Revision ID: 20260307_0026
Revises: 20260301_0025
Create Date: 2026-03-07

Creates governance tables for the six trust domains:
  - auth_events
  - user_sessions
  - support_access_grants
  - permissions
  - roles
  - role_permissions
  - protected_action_approvals
  - phi_access_audits
  - data_export_requests
  - data_provenance
  - handoff_exchange_records
  - tenant_policies
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260307_0026"
down_revision = "20260301_0025"
branch_labels = None
depends_on = None


def _table_exists(conn: sa.Connection, table: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t"
        ),
        {"t": table},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── auth_events ──────────────────────────────────────────────────────
    if not _table_exists(conn, "auth_events"):
        op.create_table(
            "auth_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column(
                "event_type",
                sa.String(64),
                nullable=False,
            ),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSON(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_auth_events_tenant_user", "auth_events", ["tenant_id", "user_id"])
        op.create_index("ix_auth_events_event_type", "auth_events", ["event_type"])

    # ── user_sessions ────────────────────────────────────────────────────
    if not _table_exists(conn, "user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(255), nullable=False, index=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── support_access_grants ────────────────────────────────────────────
    if not _table_exists(conn, "support_access_grants"):
        op.create_table(
            "support_access_grants",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("granted_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── permissions ──────────────────────────────────────────────────────
    if not _table_exists(conn, "permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(64), unique=True, nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── roles ────────────────────────────────────────────────────────────
    if not _table_exists(conn, "roles"):
        op.create_table(
            "roles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(64), unique=True, nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── role_permissions ─────────────────────────────────────────────────
    if not _table_exists(conn, "role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
            sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id"), nullable=False),
        )
        op.create_index("ix_role_permissions_role", "role_permissions", ["role_id"])

    # ── protected_action_approvals ───────────────────────────────────────
    if not _table_exists(conn, "protected_action_approvals"):
        op.create_table(
            "protected_action_approvals",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("action_type", sa.String(128), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_protected_actions_tenant_status", "protected_action_approvals", ["tenant_id", "status"])

    # ── phi_access_audits ────────────────────────────────────────────────
    if not _table_exists(conn, "phi_access_audits"):
        op.create_table(
            "phi_access_audits",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("resource_type", sa.String(64), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("access_type", sa.String(32), nullable=False),
            sa.Column("fields_accessed", postgresql.JSON(), nullable=False, server_default="[]"),
            sa.Column("reason", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_phi_access_tenant_resource", "phi_access_audits", ["tenant_id", "resource_type", "resource_id"])

    # ── data_export_requests ─────────────────────────────────────────────
    if not _table_exists(conn, "data_export_requests"):
        op.create_table(
            "data_export_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("export_type", sa.String(64), nullable=False),
            sa.Column("filters", postgresql.JSON(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
            sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("file_path", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── data_provenance ──────────────────────────────────────────────────
    if not _table_exists(conn, "data_provenance"):
        op.create_table(
            "data_provenance",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("entity_name", sa.String(128), nullable=False),
            sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("source_system", sa.String(128), nullable=False),
            sa.Column("external_id", sa.String(128), nullable=False),
            sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("raw_payload", postgresql.JSON(), nullable=True, server_default="{}"),
        )
        op.create_index("ix_data_provenance_entity", "data_provenance", ["tenant_id", "entity_name", "entity_id"])

    # ── handoff_exchange_records ─────────────────────────────────────────
    if not _table_exists(conn, "handoff_exchange_records"):
        op.create_table(
            "handoff_exchange_records",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("incidents.id"), nullable=False),
            sa.Column("destination_facility", sa.String(255), nullable=False),
            sa.Column("exchange_type", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("payload_reference", sa.String(512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── tenant_policies ──────────────────────────────────────────────────
    if not _table_exists(conn, "tenant_policies"):
        op.create_table(
            "tenant_policies",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
            sa.Column("key", sa.String(128), nullable=False, index=True),
            sa.Column("value", postgresql.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_tenant_policies_tenant_key", "tenant_policies", ["tenant_id", "key"])


def downgrade() -> None:
    tables = [
        "tenant_policies",
        "handoff_exchange_records",
        "data_provenance",
        "data_export_requests",
        "phi_access_audits",
        "protected_action_approvals",
        "role_permissions",
        "roles",
        "permissions",
        "support_access_grants",
        "user_sessions",
        "auth_events",
    ]
    conn = op.get_bind()
    for t in tables:
        if _table_exists(conn, t):
            op.drop_table(t)
