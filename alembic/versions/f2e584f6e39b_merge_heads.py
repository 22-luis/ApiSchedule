"""merge_heads

Revision ID: f2e584f6e39b
Revises: add_created_by_user_id_to_task, c1608e1076b5
Create Date: 2025-08-18 09:08:06.652334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2e584f6e39b'
down_revision: Union[str, Sequence[str], None] = ('add_created_by_user_id_to_task', 'c1608e1076b5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
