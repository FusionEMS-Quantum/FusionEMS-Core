"""Add generic domination-pattern tables: scheduling, fire ops, voice, visibility

All tables follow the DominationRepository schema:
  id UUID PK, tenant_id UUID FK, data JSONB, version INT,
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ

Revision ID: 20260316_0009
Revises: 20260316_0008
Create Date: 2026-03-16 00:09:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0009"
down_revision = "20260316_0008"
branch_labels = None
depends_on = None

_DOMINATION_TABLES = [
    # scheduling
    "coverage_rules",
    "fatigue_assessments",
    "shift_swap_requests",
    # fire ops
    "fire_apparatus_records",
    # crewlink
    "crew_paging_audit_log",
    # voice
    "visibility_elevated_access",
    "visibility_secure_links",
    "visibility_time_windows",
    "visibility_policies",
    "visibility_emergency_access",
    "visibility_kill_switch",
]


def _domination_columns() -> list:
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("data", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    for table_name in _DOMINATION_TABLES:
        op.create_table(table_name, *_domination_columns())
        op.create_index(f"ix_{table_name}_tenant_id", table_name, ["tenant_id"])
        op.create_index(f"ix_{table_name}_deleted_at", table_name, ["deleted_at"])

    # provider_credentials has specific non-JSONB columns used in raw SQL queries
    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("provider_name", sa.String(255), nullable=False),
        sa.Column("credential_type", sa.String(64), nullable=False),
        sa.Column("expiration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_provider_credentials_tenant_id", "provider_credentials", ["tenant_id"])
    op.create_index("ix_provider_credentials_expiration_date", "provider_credentials", ["expiration_date"])


def downgrade() -> None:
    op.drop_table("provider_credentials")
    for table_name in reversed(_DOMINATION_TABLES):
        op.drop_index(f"ix_{table_name}_deleted_at", table_name=table_name)
        op.drop_index(f"ix_{table_name}_tenant_id", table_name=table_name)
        op.drop_table(table_name)
