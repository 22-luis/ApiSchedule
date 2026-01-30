"""add name to qc_manual

Revision ID: add_name_to_manual
Revises: 3332f46ab036
Create Date: 2026-01-16 11:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_name_to_manual'
down_revision: Union[str, Sequence[str], None] = '3332f46ab036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add name column to qc_manual table
    op.add_column('qc_manual', sa.Column('name', sa.String(), nullable=True))
    op.create_index(op.f('ix_qc_manual_name'), 'qc_manual', ['name'], unique=False)
    
    # Initialize existing manuals with a default name if desired
    # This helps avoid None names in the dropdown initially
    op.execute("UPDATE qc_manual SET name = 'Instructivo General' WHERE name IS NULL")

def downgrade() -> None:
    op.drop_index(op.f('ix_qc_manual_name'), table_name='qc_manual')
    op.drop_column('qc_manual', 'name')
