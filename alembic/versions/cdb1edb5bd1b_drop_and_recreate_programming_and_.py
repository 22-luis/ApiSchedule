"""Drop and recreate programming and programming_task tables with UUIDs

Revision ID: cdb1edb5bd1b
Revises: a33fd1deffc3
Create Date: 2025-07-18 07:18:04.839351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdb1edb5bd1b'
down_revision: Union[str, Sequence[str], None] = '839e1a19dfc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear tabla programming
    op.create_table(
        'programming',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('team_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('teams.id'), nullable=False),
        sa.UniqueConstraint('date', 'team_id', name='_date_team_uc')
    )

    # Crear tabla de asociación programming_task
    op.create_table(
        'programming_task',
        sa.Column('programming_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('programming.id'), primary_key=True),
        sa.Column('task_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('task.id'), primary_key=True)
    )

def downgrade() -> None:
    # Eliminar tablas nuevas
    op.drop_table('programming_task')
    op.drop_table('programming')
    # (Opcional: aquí podrías recrear las tablas antiguas si lo necesitas)
