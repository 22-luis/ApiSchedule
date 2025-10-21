"""Remove lowercase accounting role

Revision ID: 70db53c84cdb
Revises: e55475148062
Create Date: 2025-10-21 12:20:50.371626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70db53c84cdb'
down_revision: Union[str, Sequence[str], None] = 'e55475148062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM('ADMIN', 'PLANNER', 'SUPERVISOR', 'USER', 'WAREHOUSE', 'ACCOUNTING')")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::text::userrole")
    op.execute("DROP TYPE userrole_old")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TYPE userrole ADD VALUE 'accounting'")
