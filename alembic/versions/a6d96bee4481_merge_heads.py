"""merge_heads

Revision ID: a6d96bee4481
Revises: a1b2c3d4e5f8, e2b7c9a8f1d4
Create Date: 2025-11-20 13:58:59.761342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6d96bee4481'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f8', 'e2b7c9a8f1d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
