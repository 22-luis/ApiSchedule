"""add comments to record_stopwatch

Revision ID: a1b2c3d4e5f8
Revises: a1b2c3d4e5f7
Create Date: 2025-11-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f8'
down_revision: Union[str, Sequence[str], None] = '73604d9579f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('record_stopwatch', sa.Column('comments', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('record_stopwatch', 'comments')
