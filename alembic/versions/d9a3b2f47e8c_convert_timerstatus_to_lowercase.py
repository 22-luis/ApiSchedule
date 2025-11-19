"""convert timerstatus enum values to lowercase

Revision ID: d9a3b2f47e8c
Revises: c313d3f26cc8
Create Date: 2025-11-18 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd9a3b2f47e8c'
down_revision: Union[str, Sequence[str], None] = 'c313d3f26cc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a new enum type with lowercase values
    op.execute("CREATE TYPE timerstatus_new AS ENUM ('running','paused','stopped');")

    # Remove any column default (can block type change), then switch the column to text so we can normalize values
    op.execute("ALTER TABLE stopwatch ALTER COLUMN status DROP DEFAULT;")
    op.execute("ALTER TABLE stopwatch ALTER COLUMN status TYPE text USING status::text;")

    # Normalize existing values to lowercase
    op.execute("UPDATE stopwatch SET status = lower(status) WHERE status IS NOT NULL;")

    # Convert the column to the new enum type
    op.execute("ALTER TABLE stopwatch ALTER COLUMN status TYPE timerstatus_new USING status::text::timerstatus_new;")

    # Drop the old type if it exists and rename the new one to the original name
    op.execute("DROP TYPE IF EXISTS timerstatus;")
    op.execute("ALTER TYPE timerstatus_new RENAME TO timerstatus;")


def downgrade() -> None:
    # Create the old enum with uppercase values
    op.execute("CREATE TYPE timerstatus_old AS ENUM ('RUNNING','PAUSED','STOPPED');")

    # Switch the column to text so we can denormalize values
    op.execute("ALTER TABLE stopwatch ALTER COLUMN status TYPE text USING status::text;")

    # Convert values back to uppercase
    op.execute("UPDATE stopwatch SET status = upper(status) WHERE status IS NOT NULL;")

    # Convert the column to the old enum type
    op.execute("ALTER TABLE stopwatch ALTER COLUMN status TYPE timerstatus_old USING status::text::timerstatus_old;")

    # Drop the current type and restore the old name
    op.execute("DROP TYPE IF EXISTS timerstatus;")
    op.execute("ALTER TYPE timerstatus_old RENAME TO timerstatus;")
