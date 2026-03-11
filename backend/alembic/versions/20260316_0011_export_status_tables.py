"""Add export status router tables (generic domination schema)

Revision ID: 20260316_0011
Revises: 20260316_0010
Create Date: 2026-03-16 00:11:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0011"
down_revision = "20260316_0010"
branch_labels = None
depends_on = None

_DOMINATION_TABLES = [
    "export_approvals",
    "export_audit_freezes",
    "export_bundles",
    "export_certificates",
    "export_escalations",
    "export_fire_mappings",
    "export_fire_normalizations",
    "export_freezes",
    "export_integrity_hashes",
    "export_locks",
    "export_notifications",
    "export_overrides",
    "export_proofs",
    "export_schedules",
    "export_throttle_config",
    "export_validation_results",
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


def downgrade() -> None:
    for table_name in reversed(_DOMINATION_TABLES):
        op.drop_index(f"ix_{table_name}_deleted_at", table_name=table_name)
        op.drop_index(f"ix_{table_name}_tenant_id", table_name=table_name)
        op.drop_table(table_name)
