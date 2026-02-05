"""add order to quality manual

Revision ID: b743835ec206
Revises: afe5f118a05f
Create Date: 2026-02-05 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b743835ec206'
down_revision = 'afe5f118a05f'
branch_labels = None
depends_on = None

def upgrade():
    # Add column order to table quality_manual
    op.add_column('quality_manual', sa.Column('order', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('quality_manual', 'order')
