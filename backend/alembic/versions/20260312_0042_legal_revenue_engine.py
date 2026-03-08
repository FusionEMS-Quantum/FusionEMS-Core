"""Legal requests revenue engine fields and payments table

Revision ID: 20260312_0042
Revises: 20260308_0041
Create Date: 2026-03-12
"""

from __future__ import annotations

from typing import Any, Union

import sqlalchemy as sa
from alembic import op as alembic_op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "20260312_0042"
down_revision: Union[str, None] = "20260308_0041"
branch_labels = None
depends_on = None


def _has_table(conn: sa.engine.Connection, name: str) -> bool:
    inspector = sa.inspect(conn)
    return name in inspector.get_table_names()


def _has_column(conn: sa.engine.Connection, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(conn)
    columns = inspector.get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def _op_call(name: str, *args: Any, **kwargs: Any) -> Any:
    operation = getattr(alembic_op, name)
    return operation(*args, **kwargs)


def _create_index_if_missing(conn: sa.engine.Connection, table_name: str, index_name: str, columns: list[str]) -> None:
    inspector = sa.inspect(conn)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name not in existing:
        _op_call("create_index", index_name, table_name, columns)


def upgrade() -> None:
    conn = _op_call("get_bind")

    if _has_table(conn, "legal_request_commands"):
        additions: list[tuple[str, sa.Column]] = [
            ("requester_category", sa.Column("requester_category", sa.String(length=64), nullable=False, server_default="other_third_party_manual_review")),
            ("workflow_state", sa.Column("workflow_state", sa.String(length=64), nullable=False, server_default="request_received")),
            ("payment_status", sa.Column("payment_status", sa.String(length=64), nullable=False, server_default="not_required")),
            ("payment_required", sa.Column("payment_required", sa.Boolean(), nullable=False, server_default=sa.text("false"))),
            ("margin_status", sa.Column("margin_status", sa.String(length=64), nullable=False, server_default="manual_review_required")),
            ("delivery_mode", sa.Column("delivery_mode", sa.String(length=32), nullable=False, server_default="secure_digital")),
            ("print_mail_requested", sa.Column("print_mail_requested", sa.Boolean(), nullable=False, server_default=sa.text("false"))),
            ("rush_requested", sa.Column("rush_requested", sa.Boolean(), nullable=False, server_default=sa.text("false"))),
            ("estimated_page_count", sa.Column("estimated_page_count", sa.Integer(), nullable=False, server_default="0")),
            ("jurisdiction_state", sa.Column("jurisdiction_state", sa.String(length=8), nullable=False, server_default="WI")),
            ("fee_quote", sa.Column("fee_quote", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"))),
            ("financial_snapshot", sa.Column("financial_snapshot", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"))),
            ("fulfillment_gate", sa.Column("fulfillment_gate", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb"))),
        ]
        for column_name, column in additions:
            if not _has_column(conn, "legal_request_commands", column_name):
                _op_call("add_column", "legal_request_commands", column)

        _create_index_if_missing(conn, "legal_request_commands", "ix_legal_request_commands_requester_category", ["requester_category"])
        _create_index_if_missing(conn, "legal_request_commands", "ix_legal_request_commands_workflow_state", ["workflow_state"])
        _create_index_if_missing(conn, "legal_request_commands", "ix_legal_request_commands_payment_status", ["payment_status"])
        _create_index_if_missing(conn, "legal_request_commands", "ix_legal_request_commands_margin_status", ["margin_status"])

    if not _has_table(conn, "legal_request_payments"):
        _op_call(
            "create_table",
            "legal_request_payments",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("legal_request_id", UUID(as_uuid=True), sa.ForeignKey("legal_request_commands.id"), nullable=False),
            sa.Column("provider", sa.String(length=32), nullable=False, server_default="stripe"),
            sa.Column("status", sa.String(length=64), nullable=False, server_default="payment_required"),
            sa.Column("amount_due_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("amount_collected_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("platform_fee_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("agency_payout_cents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=8), nullable=False, server_default="usd"),
            sa.Column("stripe_connected_account_id", sa.String(length=128), nullable=True),
            sa.Column("stripe_checkout_session_id", sa.String(length=128), nullable=True),
            sa.Column("stripe_payment_intent_id", sa.String(length=128), nullable=True),
            sa.Column("check_reference", sa.String(length=128), nullable=True),
            sa.Column("check_received_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("metadata_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        _op_call("create_index", "ix_legal_request_payments_tenant_id", "legal_request_payments", ["tenant_id"])
        _op_call("create_index", "ix_legal_request_payments_request_id", "legal_request_payments", ["legal_request_id"])
        _op_call("create_index", "ix_legal_request_payments_checkout_session_id", "legal_request_payments", ["stripe_checkout_session_id"])
        _op_call("create_index", "ix_legal_request_payments_payment_intent_id", "legal_request_payments", ["stripe_payment_intent_id"])


def downgrade() -> None:
    conn = _op_call("get_bind")

    if _has_table(conn, "legal_request_payments"):
        _op_call("drop_table", "legal_request_payments")

    if _has_table(conn, "legal_request_commands"):
        for column_name in [
            "fulfillment_gate",
            "financial_snapshot",
            "fee_quote",
            "jurisdiction_state",
            "estimated_page_count",
            "rush_requested",
            "print_mail_requested",
            "delivery_mode",
            "margin_status",
            "payment_required",
            "payment_status",
            "workflow_state",
            "requester_category",
        ]:
            if _has_column(conn, "legal_request_commands", column_name):
                _op_call("drop_column", "legal_request_commands", column_name)
