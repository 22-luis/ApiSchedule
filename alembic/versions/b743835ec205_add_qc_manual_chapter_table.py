"""add_qc_manual_chapter_table

Revision ID: b743835ec205
Revises: add_name_to_manual
Create Date: 2026-01-27 11:58:11.724433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b743835ec205'
down_revision: Union[str, Sequence[str], None] = 'add_name_to_manual'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Import UUID type for PostgreSQL
    from sqlalchemy.dialects import postgresql
    
    # Create qc_manual_chapter table
    op.create_table(
        'qc_manual_chapter',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('manual_id', sa.Integer(), nullable=False),
        sa.Column('parent_chapter_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('chapter_type', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['manual_id'], ['qc_manual.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_chapter_id'], ['qc_manual_chapter.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for foreign keys
    op.create_index('ix_qc_manual_chapter_manual_id', 'qc_manual_chapter', ['manual_id'])
    op.create_index('ix_qc_manual_chapter_parent_chapter_id', 'qc_manual_chapter', ['parent_chapter_id'])
    
    # Add chapter_id column to catalog_test
    op.add_column('catalog_test', sa.Column('chapter_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_catalog_test_chapter_id', 'catalog_test', 'qc_manual_chapter', ['chapter_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_catalog_test_chapter_id', 'catalog_test', ['chapter_id'])
    
    # Make the old chapter column nullable for backward compatibility
    op.alter_column('catalog_test', 'chapter', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove chapter_id from catalog_test
    op.drop_index('ix_catalog_test_chapter_id', 'catalog_test')
    op.drop_constraint('fk_catalog_test_chapter_id', 'catalog_test', type_='foreignkey')
    op.drop_column('catalog_test', 'chapter_id')
    
    # Restore chapter column to not nullable
    op.alter_column('catalog_test', 'chapter', nullable=False)
    
    # Drop qc_manual_chapter table
    op.drop_index('ix_qc_manual_chapter_parent_chapter_id', 'qc_manual_chapter')
    op.drop_index('ix_qc_manual_chapter_manual_id', 'qc_manual_chapter')
    op.drop_table('qc_manual_chapter')

