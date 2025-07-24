"""merge orderstatus enum and model changes

Revision ID: c46df6df72ae
Revises: c9150309f325, 0d98ef180ba7
Create Date: 2025-07-24 09:26:33.742680

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c46df6df72ae'
down_revision: Union[str, Sequence[str], None] = ('c9150309f325', '0d98ef180ba7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
