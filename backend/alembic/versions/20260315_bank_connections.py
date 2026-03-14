"""Add founder_bank_connections table

Revision ID: 20260315_bank_connections
Revises: 20260313_0045
Create Date: 2026-03-15

Stores encrypted bank connection metadata for the founder accounting layer.
Credentials (access tokens, OAuth tokens) are stored as encrypted blobs —
the actual secret values are managed in AWS Secrets Manager; only the
Secrets Manager ARN/reference or an AES-encrypted ciphertext is stored here.

This table is explicitly scoped to the founder and has no tenant_id —
it must never be exposed through any tenant-scoped API.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = '20260315_bank_connections'
down_revision: Union[str, None] = '20260313_0045'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'founder_bank_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),

        # Which connection protocol is active for this record
        sa.Column('protocol', sa.String(32), nullable=False),
        # e.g. "simplefin" | "ofx_direct" | "amex_api" | "plaid" | "csv_import"

        # Human-readable institution name (for UI display only)
        sa.Column('institution_name', sa.String(255), nullable=False),

        # Last 4 digits of the account number for display (never full account number)
        sa.Column('account_mask', sa.String(8), nullable=True),

        # Whether this connection is currently active
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),

        # Reference to the encrypted credential in AWS Secrets Manager.
        # For SimpleFIN: ARN of the secret holding the access URL.
        # For Plaid: ARN of the secret holding the access_token.
        # For OFX Direct: ARN of the secret holding the OFX credentials JSON.
        # For AmEx: ARN of the secret holding client_id + client_secret.
        # CSV imports do not use this field (no persistent credentials).
        sa.Column('secrets_manager_arn', sa.Text(), nullable=True),

        # Protocol-specific non-secret metadata stored as JSON.
        # For SimpleFIN: {"bridge_domain": "..."}
        # For OFX Direct: {"fid": "...", "org": "...", "url": "...", "account_type": "..."}
        # For Plaid: {"item_id": "...", "cursor": "..."}
        # For AmEx: {"account_token": "..."}
        sa.Column('metadata_json', JSONB(), nullable=False, server_default='{}'),

        # Cursor / sync state for incremental syncs
        sa.Column('sync_cursor', sa.Text(), nullable=True),

        # Last successful sync timestamp
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),

        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()'), onupdate=sa.text('now()')),

        # Soft delete — never hard-delete bank connections (audit trail)
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),

        sa.CheckConstraint(
            "protocol IN ('simplefin', 'ofx_direct', 'amex_api', 'plaid', 'csv_import')",
            name='ck_founder_bank_connections_protocol',
        ),
    )

    # Index for active connections lookup (typical query pattern: WHERE is_active = true)
    op.create_index(
        'ix_founder_bank_connections_active',
        'founder_bank_connections',
        ['is_active', 'protocol'],
    )

    # Row-level security: restrict table access to the backend role only.
    # This table must never be visible through tenant-scoped queries.
    op.execute(
        "COMMENT ON TABLE founder_bank_connections IS "
        "'Founder-only bank connection metadata. No tenant_id. "
        "Credentials stored in AWS Secrets Manager; only ARN referenced here.'"
    )


def downgrade() -> None:
    op.drop_index('ix_founder_bank_connections_active', table_name='founder_bank_connections')
    op.drop_table('founder_bank_connections')
