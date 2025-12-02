"""add_fabricated_quantity_to_order

Revision ID: bb5872d5ef02
Revises: 780c645f6ae9
Create Date: 2025-12-02 08:44:26.987480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bb5872d5ef02'
down_revision: Union[str, Sequence[str], None] = '780c645f6ae9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('order', sa.Column('fabricated_quantity', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('order', 'fabricated_quantity')
