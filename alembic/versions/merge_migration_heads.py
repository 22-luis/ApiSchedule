
"""merge migration heads"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7' # Unique revision ID for the merge
down_revision: Union[str, Sequence[str], None] = ('e5feb0197260', 'e8252fe8bc10')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
