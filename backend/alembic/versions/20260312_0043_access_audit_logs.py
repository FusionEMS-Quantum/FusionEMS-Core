# pyright: reportGeneralTypeIssues=false
"""Access Audit Logs

Revision ID: 20260312_0043
Revises: 20260312_0042
Create Date: 2026-03-10

"""

# pylint: disable=no-member,not-callable,no-name-in-module

from alembic import op  # pyright: ignore[reportAttributeAccessIssue]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260312_0043"
down_revision = "20260312_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("actor_role", sa.String(64), nullable=False),
        sa.Column("required_role", sa.String(64), nullable=False),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "ix_access_audit_logs_tenant_created_at",
        "access_audit_logs",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_access_audit_logs_tenant_created_at", table_name="access_audit_logs")
    op.drop_table("access_audit_logs")
