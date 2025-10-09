"""Convert quantity fields to Float

Revision ID: f8f6e9e4c4e0
Revises: b1745a47036c
Create Date: 2025-10-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8f6e9e4c4e0'
down_revision = 'b1745a47036c'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('task', 'quantity',
               existing_type=sa.Integer(),
               type_=sa.Float(),
               existing_nullable=True)
    op.alter_column('programming_task', 'real_quantity',
               existing_type=sa.Integer(),
               type_=sa.Float(),
               existing_nullable=True)
    op.alter_column('order', 'quantity',
               existing_type=sa.Integer(),
               type_=sa.Float(),
               existing_nullable=True)
    op.alter_column('order', 'received_quantity',
               existing_type=sa.Integer(),
               type_=sa.Float(),
               existing_nullable=True)
    op.alter_column('order', 'missing_quantity',
               existing_type=sa.Integer(),
               type_=sa.Float(),
               existing_nullable=True)


def downgrade():
    op.alter_column('task', 'quantity',
               existing_type=sa.Float(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('programming_task', 'real_quantity',
               existing_type=sa.Float(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('order', 'quantity',
               existing_type=sa.Float(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('order', 'received_quantity',
               existing_type=sa.Float(),
               type_=sa.Integer(),
               existing_nullable=True)
    op.alter_column('order', 'missing_quantity',
               existing_type=sa.Float(),
               type_=sa.Integer(),
               existing_nullable=True)
