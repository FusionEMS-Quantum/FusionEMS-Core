"""TransportLink: add facility_access_requests table

Revision ID: 20260308_0040
Revises: 20260308_0039
Create Date: 2026-03-08

Adds the facility_access_requests tenant-scoped table used by the
TransportLink portal access request workflow (unauthenticated facility
onboarding submissions reviewed by ops staff).
"""

from __future__ import annotations

from typing import Any, Union, cast

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

op = cast(Any, op)

revision: str = "20260308_0040"
down_revision: Union[str, None] = "20260308_0039"
branch_labels = None
depends_on = None


def _has_table(conn: sa.engine.Connection, name: str) -> bool:
    insp = sa.inspect(conn)
    return name in insp.get_table_names()


def _create_tenant_json_table(name: str) -> None:
    """Create a standard tenant-scoped JSONB domination table with RLS."""
    op.create_table(
        name,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        f'CREATE POLICY "{name}_tenant_isolation" ON "{name}" '
        f"USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Facility portal access requests — submitted by facilities before being
    # granted a portal account.  Not tenant-scoped in the traditional sense
    # (uses a system tenant UUID for unauthenticated submissions) but follows
    # the same physical schema for consistency.
    if not _has_table(conn, "facility_access_requests"):
        _create_tenant_json_table("facility_access_requests")
        # Index on work_email for deduplication lookups
        op.execute(
            "CREATE INDEX ix_facility_access_requests_email "
            "ON facility_access_requests ((data->>'work_email'));"
        )
        op.execute(
            "CREATE INDEX ix_facility_access_requests_status "
            "ON facility_access_requests ((data->>'status'));"
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "facility_access_requests"):
        op.drop_table("facility_access_requests")
