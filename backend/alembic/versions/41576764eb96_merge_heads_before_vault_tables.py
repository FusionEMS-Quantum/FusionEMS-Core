"""merge_heads_before_vault_tables

Revision ID: 41576764eb96
Revises: 20260312_0043, vault_lock_enforcement_001
Create Date: 2026-03-10 22:23:27.527463

"""

from typing import Sequence, Union


revision: str = '41576764eb96'
down_revision: Union[str, None] = ('20260312_0043', 'vault_lock_enforcement_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
