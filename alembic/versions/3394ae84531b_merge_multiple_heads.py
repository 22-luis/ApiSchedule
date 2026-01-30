"""merge_multiple_heads

Revision ID: 3394ae84531b
Revises: 0c7411572b18, a86a9dc280d1
Create Date: 2026-01-29 11:26:16.109042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3394ae84531b'
down_revision: Union[str, Sequence[str], None] = ('0c7411572b18', 'a86a9dc280d1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
