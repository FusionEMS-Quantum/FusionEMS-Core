"""Legal Requests Command MVP tables

Revision ID: 20260308_0041
Revises: 20260308_0040
Create Date: 2026-03-08
"""

from __future__ import annotations

from typing import Any, Union

import sqlalchemy as sa
from alembic import op as alembic_op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "20260308_0041"
down_revision: Union[str, None] = "20260308_0040"
branch_labels = None
depends_on = None


def _has_table(conn: sa.engine.Connection, name: str) -> bool:
    inspector = sa.inspect(conn)
    return name in inspector.get_table_names()


def _op_call(name: str, *args: Any, **kwargs: Any) -> Any:
    operation = getattr(alembic_op, name)
    return operation(*args, **kwargs)


def upgrade() -> None:
    conn = _op_call("get_bind")

    if not _has_table(conn, "legal_request_commands"):
        _op_call(
            "create_table",
            "legal_request_commands",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
            sa.Column("request_type", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False, server_default="received"),
            sa.Column("requesting_party", sa.String(length=255), nullable=False),
            sa.Column("requester_name", sa.String(length=255), nullable=False),
            sa.Column("requesting_entity", sa.String(length=255), nullable=True),
            sa.Column("patient_first_name", sa.String(length=128), nullable=True),
            sa.Column("patient_last_name", sa.String(length=128), nullable=True),
            sa.Column("patient_dob", sa.Date(), nullable=True),
            sa.Column("mrn", sa.String(length=128), nullable=True),
            sa.Column("csn", sa.String(length=128), nullable=True),
            sa.Column("requested_date_from", sa.Date(), nullable=True),
            sa.Column("requested_date_to", sa.Date(), nullable=True),
            sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivery_preference", sa.String(length=64), nullable=False, server_default="secure_one_time_link"),
            sa.Column("triage_summary", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("missing_items", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("required_document_checklist", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("review_gate", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("redaction_mode", sa.String(length=96), nullable=False, server_default="court_safe_minimum_necessary"),
            sa.Column("review_notes", sa.Text(), nullable=True),
            sa.Column("reviewed_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("packet_manifest", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("packet_generated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("intake_token_hash", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        _op_call("create_index", "ix_legal_request_commands_tenant_id", "legal_request_commands", ["tenant_id"])
        _op_call("create_index", "ix_legal_request_commands_clinical_record_id", "legal_request_commands", ["clinical_record_id"])
        _op_call("create_index", "ix_legal_request_commands_request_type", "legal_request_commands", ["request_type"])
        _op_call("create_index", "ix_legal_request_commands_status", "legal_request_commands", ["status"])
        _op_call("create_index", "ix_legal_request_commands_deadline_at", "legal_request_commands", ["deadline_at"])
        _op_call("create_index", "ix_legal_request_commands_intake_token_hash", "legal_request_commands", ["intake_token_hash"])

    if not _has_table(conn, "legal_request_uploads"):
        _op_call(
            "create_table",
            "legal_request_uploads",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("legal_request_id", UUID(as_uuid=True), sa.ForeignKey("legal_request_commands.id"), nullable=False),
            sa.Column("document_kind", sa.String(length=128), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("mime_type", sa.String(length=128), nullable=False),
            sa.Column("storage_uri", sa.String(length=1024), nullable=False),
            sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("checksum_sha256", sa.String(length=128), nullable=True),
            sa.Column("uploaded_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("metadata_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        _op_call("create_index", "ix_legal_request_uploads_tenant_id", "legal_request_uploads", ["tenant_id"])
        _op_call("create_index", "ix_legal_request_uploads_request_id", "legal_request_uploads", ["legal_request_id"])
        _op_call("create_index", "ix_legal_request_uploads_kind", "legal_request_uploads", ["document_kind"])

    if not _has_table(conn, "legal_delivery_links"):
        _op_call(
            "create_table",
            "legal_delivery_links",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
            sa.Column("legal_request_id", UUID(as_uuid=True), sa.ForeignKey("legal_request_commands.id"), nullable=False),
            sa.Column("token_hash", sa.String(length=128), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("recipient_hint", sa.String(length=255), nullable=True),
            sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("download_ip", sa.String(length=128), nullable=True),
            sa.Column("download_user_agent", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        _op_call("create_index", "ix_legal_delivery_links_tenant_id", "legal_delivery_links", ["tenant_id"])
        _op_call("create_index", "ix_legal_delivery_links_request_id", "legal_delivery_links", ["legal_request_id"])
        _op_call("create_index", "ix_legal_delivery_links_token_hash", "legal_delivery_links", ["token_hash"])
        _op_call("create_index", "ix_legal_delivery_links_expires_at", "legal_delivery_links", ["expires_at"])


def downgrade() -> None:
    conn = _op_call("get_bind")
    if _has_table(conn, "legal_delivery_links"):
        _op_call("drop_table", "legal_delivery_links")
    if _has_table(conn, "legal_request_uploads"):
        _op_call("drop_table", "legal_request_uploads")
    if _has_table(conn, "legal_request_commands"):
        _op_call("drop_table", "legal_request_commands")
