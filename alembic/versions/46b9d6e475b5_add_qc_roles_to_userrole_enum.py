"""add qc roles to userrole enum

Revision ID: 46b9d6e475b5
Revises: 23bdd10ea6bb
Create Date: 2025-12-18 10:39:38.269072

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46b9d6e475b5'
down_revision: Union[str, Sequence[str], None] = '23bdd10ea6bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'QC_ENGINEER'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'QC_TECHNICIAN'")


def downgrade() -> None:
    """Downgrade schema."""
    # Values cannot be easily removed from a PostgreSQL enum
    pass
