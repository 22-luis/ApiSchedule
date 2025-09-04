"""Add manufactured status to OrderStatus enum

Revision ID: f6dab950833f
Revises: 06807494578e
Create Date: 2025-09-04 09:53:42.897408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6dab950833f'
down_revision: Union[str, Sequence[str], None] = '06807494578e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add 'manufactured' value to the OrderStatus enum
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'manufactured'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum type, which is complex
    # For now, we'll leave the value in place
    pass
