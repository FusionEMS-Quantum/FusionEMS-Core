"""Add patient enrichment fields — deceased_indicator, identity_state,
language_preference, interpreter_required.

Supports CRM Directive Part 3 (Patient Identity) enrichment of the
canonical patient record.

Revision ID: 20260311_0035
Revises: 20260310_0034
Create Date: 2026-03-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260311_0035"
down_revision: Union[str, None] = "20260310_0034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "deceased_indicator",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "identity_state",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'PROFILE_CREATED'"),
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "language_preference",
            sa.String(16),
            nullable=True,
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "interpreter_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("patients", "interpreter_required")
    op.drop_column("patients", "language_preference")
    op.drop_column("patients", "identity_state")
    op.drop_column("patients", "deceased_indicator")
