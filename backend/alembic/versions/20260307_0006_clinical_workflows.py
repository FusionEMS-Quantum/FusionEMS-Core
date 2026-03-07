"""clinical workflows: qa, amendments, handoff, signatures, sync_queue, validation_snapshots

Revision ID: 20260307_0006
Revises: 20260227_0005
Create Date: 2026-03-07 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260307_0006"
down_revision: str | None = "20260301_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Standard function used in all domination tables
_STANDARD_COLS = [
    sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
    sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
]


def _std_cols():
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    ]


def upgrade() -> None:
    # QA Reviews — one review session per chart, stores flags and decision
    op.create_table(
        "epcr_qa_reviews",
        *_std_cols(),
        sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="not_reviewed"),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_epcr_qa_reviews_tenant_id", "epcr_qa_reviews", ["tenant_id"])
    op.create_index("ix_epcr_qa_reviews_chart_id", "epcr_qa_reviews", ["chart_id"])
    op.create_index("ix_epcr_qa_reviews_status", "epcr_qa_reviews", ["status"])
    op.execute(sa.text('ALTER TABLE "epcr_qa_reviews" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(
        'CREATE POLICY "tenant_isolation" ON "epcr_qa_reviews" '
        'USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid)'
    ))

    # Amendments — explicit amendment requests against locked charts
    op.create_table(
        "epcr_amendments",
        *_std_cols(),
        sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("ix_epcr_amendments_tenant_id", "epcr_amendments", ["tenant_id"])
    op.create_index("ix_epcr_amendments_chart_id", "epcr_amendments", ["chart_id"])
    op.create_index("ix_epcr_amendments_status", "epcr_amendments", ["status"])
    op.execute(sa.text('ALTER TABLE "epcr_amendments" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(
        'CREATE POLICY "tenant_isolation" ON "epcr_amendments" '
        'USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid)'
    ))

    # Handoff packets — clinical communication artifact for receiving facility
    op.create_table(
        "epcr_handoff_packets",
        *_std_cols(),
        sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="handoff_not_prepared"),
        sa.Column("recipient_facility", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_epcr_handoff_packets_tenant_id", "epcr_handoff_packets", ["tenant_id"])
    op.create_index("ix_epcr_handoff_packets_chart_id", "epcr_handoff_packets", ["chart_id"])
    op.execute(sa.text('ALTER TABLE "epcr_handoff_packets" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(
        'CREATE POLICY "tenant_isolation" ON "epcr_handoff_packets" '
        'USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid)'
    ))

    # Chart signatures — captured signatures for treatment, refusal, HIPAA, handoff
    op.create_table(
        "epcr_chart_signatures",
        *_std_cols(),
        sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signer_role", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_epcr_chart_signatures_tenant_id", "epcr_chart_signatures", ["tenant_id"])
    op.create_index("ix_epcr_chart_signatures_chart_id", "epcr_chart_signatures", ["chart_id"])
    op.execute(sa.text('ALTER TABLE "epcr_chart_signatures" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(
        'CREATE POLICY "tenant_isolation" ON "epcr_chart_signatures" '
        'USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid)'
    ))

    # Offline sync queue — persists charts queued for sync, tracks retries
    op.create_table(
        "epcr_sync_queue",
        *_std_cols(),
        sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_epcr_sync_queue_tenant_id", "epcr_sync_queue", ["tenant_id"])
    op.create_index("ix_epcr_sync_queue_chart_id", "epcr_sync_queue", ["chart_id"])
    op.create_index("ix_epcr_sync_queue_status", "epcr_sync_queue", ["status"])
    op.execute(sa.text('ALTER TABLE "epcr_sync_queue" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(
        'CREATE POLICY "tenant_isolation" ON "epcr_sync_queue" '
        'USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid)'
    ))

    # Validation snapshots — point-in-time result of full clinical validation
    op.create_table(
        "epcr_validation_snapshots",
        *_std_cols(),
        sa.Column("chart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_status", sa.String(length=64), nullable=False),
        sa.Column("has_blocking", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_epcr_validation_snapshots_tenant_id", "epcr_validation_snapshots", ["tenant_id"])
    op.create_index("ix_epcr_validation_snapshots_chart_id", "epcr_validation_snapshots", ["chart_id"])
    op.execute(sa.text('ALTER TABLE "epcr_validation_snapshots" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(
        'CREATE POLICY "tenant_isolation" ON "epcr_validation_snapshots" '
        'USING (tenant_id = current_setting(\'app.tenant_id\', true)::uuid)'
    ))


def downgrade() -> None:
    for table in [
        "epcr_validation_snapshots",
        "epcr_sync_queue",
        "epcr_chart_signatures",
        "epcr_handoff_packets",
        "epcr_amendments",
        "epcr_qa_reviews",
    ]:
        op.drop_table(table)
