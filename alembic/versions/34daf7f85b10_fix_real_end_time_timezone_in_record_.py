"""fix_real_end_time_timezone_in_record_stopwatch

Revision ID: 34daf7f85b10
Revises: 01ba919d1c29
Create Date: 2026-03-26 12:17:20.810373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34daf7f85b10'
down_revision: Union[str, Sequence[str], None] = '01ba919d1c29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Change all timestamp columns to TIMESTAMP WITHOUT TIME ZONE in record_stopwatch and stopwatch."""
    # record_stopwatch table
    op.execute('ALTER TABLE record_stopwatch ALTER COLUMN real_end_time TYPE TIMESTAMP WITHOUT TIME ZONE USING real_end_time::timestamp')
    op.execute('ALTER TABLE record_stopwatch ALTER COLUMN real_start_time TYPE TIMESTAMP WITHOUT TIME ZONE USING real_start_time::timestamp')
    op.execute('ALTER TABLE record_stopwatch ALTER COLUMN creation_date TYPE TIMESTAMP WITHOUT TIME ZONE USING creation_date::timestamp')
    
    # stopwatch table
    op.execute('ALTER TABLE stopwatch ALTER COLUMN real_end_time TYPE TIMESTAMP WITHOUT TIME ZONE USING real_end_time::timestamp')
    op.execute('ALTER TABLE stopwatch ALTER COLUMN real_start_time TYPE TIMESTAMP WITHOUT TIME ZONE USING real_start_time::timestamp')
    op.execute('ALTER TABLE stopwatch ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at::timestamp')
    op.execute('ALTER TABLE stopwatch ALTER COLUMN update_at TYPE TIMESTAMP WITHOUT TIME ZONE USING update_at::timestamp')


def downgrade() -> None:
    """Downgrade schema - Change all columns back to TIMESTAMP WITH TIME ZONE."""
    # record_stopwatch table
    op.execute('ALTER TABLE record_stopwatch ALTER COLUMN real_end_time TYPE TIMESTAMP WITH TIME ZONE USING real_end_time::timestamptz')
    op.execute('ALTER TABLE record_stopwatch ALTER COLUMN real_start_time TYPE TIMESTAMP WITH TIME ZONE USING real_start_time::timestamptz')
    op.execute('ALTER TABLE record_stopwatch ALTER COLUMN creation_date TYPE TIMESTAMP WITH TIME ZONE USING creation_date::timestamptz')
    
    # stopwatch table
    op.execute('ALTER TABLE stopwatch ALTER COLUMN real_end_time TYPE TIMESTAMP WITH TIME ZONE USING real_end_time::timestamptz')
    op.execute('ALTER TABLE stopwatch ALTER COLUMN real_start_time TYPE TIMESTAMP WITH TIME ZONE USING real_start_time::timestamptz')
    op.execute('ALTER TABLE stopwatch ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at::timestamptz')
    op.execute('ALTER TABLE stopwatch ALTER COLUMN update_at TYPE TIMESTAMP WITH TIME ZONE USING update_at::timestamptz')
