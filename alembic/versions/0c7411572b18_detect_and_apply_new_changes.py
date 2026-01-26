"""Detect and apply new changes

Revision ID: 0c7411572b18
Revises: 36be1e0e135b
Create Date: 2026-01-24 10:54:47.776086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c7411572b18'
down_revision: Union[str, Sequence[str], None] = '36be1e0e135b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('order', sa.Column('is_hidden', sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('order', 'is_hidden')
