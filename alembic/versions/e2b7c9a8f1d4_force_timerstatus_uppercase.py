"""force timerstatus enum to uppercase and ensure stopwatch.status exists

Revision ID: e2b7c9a8f1d4
Revises: d9a3b2f47e8c
Create Date: 2025-11-18 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e2b7c9a8f1d4'
down_revision: Union[str, Sequence[str], None] = 'd9a3b2f47e8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This DO block is guarded so it works whether or not the column/type already exist.
    op.execute(r"""
    DO $$
    BEGIN
        -- Create a new type with uppercase labels
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'timerstatus_new') THEN
            CREATE TYPE timerstatus_new AS ENUM ('RUNNING','PAUSED','STOPPED');
        END IF;

        -- If the column exists, drop default, cast to text, normalize to UPPER, then cast to new enum
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='stopwatch' AND column_name='status') THEN
            EXECUTE 'ALTER TABLE stopwatch ALTER COLUMN status DROP DEFAULT';
            EXECUTE 'ALTER TABLE stopwatch ALTER COLUMN status TYPE text USING status::text';
            EXECUTE 'UPDATE stopwatch SET status = upper(status) WHERE status IS NOT NULL';
            EXECUTE 'ALTER TABLE stopwatch ALTER COLUMN status TYPE timerstatus_new USING status::text::timerstatus_new';
        END IF;

        -- Drop old timerstatus if it exists and rename the new one
        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'timerstatus') THEN
            EXECUTE 'DROP TYPE timerstatus';
        END IF;
        EXECUTE 'ALTER TYPE timerstatus_new RENAME TO timerstatus';
    END
    $$;
    """)


def downgrade() -> None:
    # Downgrade: create lowercase type and convert values back to lowercase if the column exists
    op.execute(r"""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'timerstatus_lower') THEN
            CREATE TYPE timerstatus_lower AS ENUM ('running','paused','stopped');
        END IF;

        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='stopwatch' AND column_name='status') THEN
            EXECUTE 'ALTER TABLE stopwatch ALTER COLUMN status DROP DEFAULT';
            EXECUTE 'ALTER TABLE stopwatch ALTER COLUMN status TYPE text USING status::text';
            EXECUTE 'UPDATE stopwatch SET status = lower(status) WHERE status IS NOT NULL';
            EXECUTE 'ALTER TABLE stopwatch ALTER COLUMN status TYPE timerstatus_lower USING status::text::timerstatus_lower';
        END IF;

        IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'timerstatus') THEN
            EXECUTE 'DROP TYPE timerstatus';
        END IF;
        EXECUTE 'ALTER TYPE timerstatus_lower RENAME TO timerstatus';
    END
    $$;
    """)
