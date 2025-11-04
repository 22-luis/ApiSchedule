from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14ceb72e4a02'
down_revision: Union[str, Sequence[str], None] = '7a9a16ce9264'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'TIMEKEEPER'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ACCOUNTING'")


def downgrade() -> None:
    """Downgrade schema."""
    # The values TIMEKEEPER and ACCOUNTING will be left in the enum
    pass