"""manual update role enum

Revision ID: 5d0962f7d0c5
Revises: 280a1cd0bb63
Create Date: 2025-10-24 11:38:42.049750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d0962f7d0c5'
down_revision: Union[str, Sequence[str], None] = '280a1cd0bb63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('users', 'role',
               existing_type=sa.Enum('ADMIN', 'PLANNER', 'SUPERVISOR', 'USER', 'WAREHOUSE', name='userrole'),
               type_=sa.Enum('ADMIN', 'PLANNER', 'SUPERVISOR', 'TIMEKEEPER', 'USER', 'WAREHOUSE', 'ACCOUNTING', name='userrole'),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'role',
               existing_type=sa.Enum('ADMIN', 'PLANNER', 'SUPERVISOR', 'TIMEKEEPER', 'USER', 'WAREHOUSE', 'ACCOUNTING', name='userrole'),
               type_=sa.Enum('ADMIN', 'PLANNER', 'SUPERVISOR', 'USER', 'WAREHOUSE', name='userrole'),
               existing_nullable=True)