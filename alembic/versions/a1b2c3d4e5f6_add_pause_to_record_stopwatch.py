"""add pause to record stopwatch

Revision ID: a1b2c3d4e5f6
Revises: 14ceb72e4a02
Create Date: 2025-10-29 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '14ceb72e4a02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    op.drop_column('record_stopwatch', 'is_paused')
    op.drop_column('record_stopwatch', 'accumulated_duration')
