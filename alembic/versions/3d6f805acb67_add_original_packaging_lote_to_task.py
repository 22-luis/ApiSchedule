"""add_original_packaging_lote_to_task

Revision ID: 3d6f805acb67
Revises: bb5872d5ef02
Create Date: 2025-12-08 11:02:31.378222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3d6f805acb67'
down_revision: Union[str, Sequence[str], None] = 'bb5872d5ef02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add original_packaging_lote column to task table."""
    op.add_column('task', sa.Column('original_packaging_lote', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove original_packaging_lote column from task table."""
    op.drop_column('task', 'original_packaging_lote')
