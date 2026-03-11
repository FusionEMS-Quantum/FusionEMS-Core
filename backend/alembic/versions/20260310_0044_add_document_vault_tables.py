"""Add document vault tables

Revision ID: 20260310_0044
Revises: 41576764eb96
Create Date: 2026-03-10
"""
# pylint: disable=no-name-in-module

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op  # pyright: ignore[reportAttributeAccessIssue]
from sqlalchemy.dialects import postgresql

revision: str = "20260310_0044"
down_revision: Union[str, None] = "41576764eb96"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # vault_definitions — the 12-vault catalog (seeded once on startup)
    op.create_table(
        "vault_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("vault_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("s3_prefix", sa.String(length=256), nullable=False),
        sa.Column("retention_class", sa.String(length=64), nullable=False),
        sa.Column("retention_years", sa.Integer(), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("is_permanent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_legal_hold_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("icon_key", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_id", name="uq_vault_definitions_vault_id"),
    )
    op.create_index("ix_vault_definitions_vault_id", "vault_definitions", ["vault_id"], unique=True)

    # vault_documents — the primary document records
    op.create_table(
        "vault_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("vault_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("s3_bucket", sa.String(length=256), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("s3_version_id", sa.String(length=256), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("lock_state", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("lock_history", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("retention_class", sa.String(length=64), nullable=True),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ocr_status", sa.String(length=32), nullable=True, server_default="pending"),
        sa.Column("ocr_job_id", sa.String(length=256), nullable=True),
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("ocr_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_classification_status", sa.String(length=32), nullable=True, server_default="pending"),
        sa.Column("ai_document_type", sa.String(length=128), nullable=True),
        sa.Column("ai_tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("ai_classified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("doc_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("addenda", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("uploaded_by_display", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_documents_vault_id", "vault_documents", ["vault_id"])
    op.create_index("ix_vault_documents_lock_state", "vault_documents", ["lock_state"])

    # vault_document_versions — S3 version history
    op.create_table(
        "vault_document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("s3_bucket", sa.String(length=256), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("s3_version_id", sa.String(length=256), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["vault_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_document_versions_document_id", "vault_document_versions", ["document_id"])

    # vault_smart_folders — user-defined or AI-generated folder groupings
    op.create_table(
        "vault_smart_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("vault_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("icon_key", sa.String(length=64), nullable=True),
        sa.Column("document_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # vault_export_packages — export package manifests
    op.create_table(
        "vault_export_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("package_name", sa.String(length=256), nullable=False),
        sa.Column("export_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bytes", sa.BigInteger(), nullable=True),
        sa.Column("s3_bucket", sa.String(length=256), nullable=True),
        sa.Column("s3_key", sa.String(length=1024), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_export_packages_status", "vault_export_packages", ["status"])

    # vault_package_manifest_items — individual documents in a package
    op.create_table(
        "vault_package_manifest_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path_in_zip", sa.String(length=512), nullable=False),
        sa.Column("s3_bucket", sa.String(length=256), nullable=False),
        sa.Column("s3_key", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["package_id"], ["vault_export_packages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # vault_audit_entries — append-only audit trail
    op.create_table(
        "vault_audit_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vault_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_display", sa.String(length=256), nullable=True),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vault_audit_entries_document_id", "vault_audit_entries", ["document_id"])
    op.create_index("ix_vault_audit_entries_action", "vault_audit_entries", ["action"])
    op.create_index("ix_vault_audit_entries_occurred_at", "vault_audit_entries", ["occurred_at"])

    # vault_retention_policies — per-vault override of retention schedules
    op.create_table(
        "vault_retention_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column("vault_id", sa.String(length=64), nullable=False),
        sa.Column("retention_years", sa.Integer(), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("is_permanent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vault_id", name="uq_vault_retention_policies_vault_id"),
    )


def downgrade() -> None:
    op.drop_table("vault_retention_policies")
    op.drop_table("vault_audit_entries")
    op.drop_table("vault_package_manifest_items")
    op.drop_table("vault_export_packages")
    op.drop_table("vault_smart_folders")
    op.drop_table("vault_document_versions")
    op.drop_table("vault_documents")
    op.drop_table("vault_definitions")
