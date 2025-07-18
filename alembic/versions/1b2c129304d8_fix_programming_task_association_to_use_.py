"""Fix programming_task association to use UUID for programming_id

Revision ID: 1b2c129304d8
Revises: cdb1edb5bd1b
Create Date: 2025-07-18 07:42:58.779842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b2c129304d8'
down_revision: Union[str, Sequence[str], None] = '839e1a19dfc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('programming_task')
    op.create_table(
        'programming_task',
        sa.Column('programming_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('programming.id'), primary_key=True),
        sa.Column('task_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('task.id'), primary_key=True)
    )


def downgrade() -> None:
    op.drop_table('programming_task')
    op.create_table(
        'programming_task',
        sa.Column('programming_id', sa.Integer(), sa.ForeignKey('programming.id'), primary_key=True),
        sa.Column('task_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('task.id'), primary_key=True)
    )
