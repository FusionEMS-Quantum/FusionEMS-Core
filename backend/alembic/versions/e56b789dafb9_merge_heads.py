"""Merge heads

Revision ID: e56b789dafb9
Revises: 20260307_0006, 20260307_0029
Create Date: 2026-03-07 14:32:08.343267

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e56b789dafb9'
down_revision: Union[str, None] = ('20260307_0006', '20260307_0029')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
