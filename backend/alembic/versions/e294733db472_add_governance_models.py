"""Add governance models

Revision ID: e294733db472
Revises: e56b789dafb9
Create Date: 2026-03-07 14:32:44.376002

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'e294733db472'
down_revision: Union[str, None] = 'e56b789dafb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use execute to avoid string-enum restrictions
    
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    op.create_table(
        'role_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'auth_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(op.f('ix_auth_events_tenant_id'), 'auth_events', ['tenant_id'], unique=False)

    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_tenant_id'), 'user_sessions', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_token_hash'), 'user_sessions', ['token_hash'], unique=False)

    op.create_table(
        'support_access_grants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('granted_to_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['granted_to_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_support_access_grants_tenant_id'), 'support_access_grants', ['tenant_id'], unique=False)

    op.create_table(
        'protected_action_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action_type', sa.String(length=128), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requested_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_protected_action_approvals_tenant_id'), 'protected_action_approvals', ['tenant_id'], unique=False)

    op.create_table(
        'phi_access_audits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_type', sa.String(length=32), nullable=False),
        sa.Column('fields_accessed', sa.JSON(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_phi_access_audits_tenant_id'), 'phi_access_audits', ['tenant_id'], unique=False)

    op.create_table(
        'data_export_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('export_type', sa.String(length=64), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_export_requests_tenant_id'), 'data_export_requests', ['tenant_id'], unique=False)

    op.create_table(
        'data_provenance',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_name', sa.String(length=128), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_system', sa.String(length=128), nullable=False),
        sa.Column('external_id', sa.String(length=128), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('raw_payload', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_data_provenance_tenant_id'), 'data_provenance', ['tenant_id'], unique=False)

    op.create_table(
        'handoff_exchange_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('destination_facility', sa.String(length=255), nullable=False),
        sa.Column('exchange_type', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('payload_reference', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_handoff_exchange_records_tenant_id'), 'handoff_exchange_records', ['tenant_id'], unique=False)

    op.create_table(
        'tenant_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenant_policies_key'), 'tenant_policies', ['key'], unique=False)
    op.create_index(op.f('ix_tenant_policies_tenant_id'), 'tenant_policies', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('tenant_policies')
    op.drop_table('handoff_exchange_records')
    op.drop_table('data_provenance')
    op.drop_table('data_export_requests')
    op.drop_table('phi_access_audits')
    op.drop_table('protected_action_approvals')
    op.drop_table('support_access_grants')
    op.drop_table('user_sessions')
    op.drop_table('auth_events')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')

