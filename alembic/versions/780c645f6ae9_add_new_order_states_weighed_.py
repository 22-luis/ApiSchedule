"""add_new_order_states_weighed_manufactured_packaged

Revision ID: 780c645f6ae9
Revises: 61dcab53241a
Create Date: 2025-11-28 11:29:07.483217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '780c645f6ae9'
down_revision: Union[str, Sequence[str], None] = '61dcab53241a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add new order states to the OrderStatus enum:
    - weighed: Order has been weighed
    - manufactured: Order has been manufactured/fabricated
    - packaged: Order has been packaged
    
    These states provide more granular tracking of the order lifecycle.
    """
    # For PostgreSQL, we need to add new enum values to the existing type
    # This is done using ALTER TYPE ... ADD VALUE
    
    # Add 'weighed' state if it doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'weighed' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'orderstatus'
                )
            ) THEN
                ALTER TYPE orderstatus ADD VALUE 'weighed';
            END IF;
        END
        $$;
    """)
    
    # Add 'manufactured' state if it doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'manufactured' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'orderstatus'
                )
            ) THEN
                ALTER TYPE orderstatus ADD VALUE 'manufactured';
            END IF;
        END
        $$;
    """)
    
    # Add 'packaged' state if it doesn't exist
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'packaged' 
                AND enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = 'orderstatus'
                )
            ) THEN
                ALTER TYPE orderstatus ADD VALUE 'packaged';
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    """
    Downgrade is not supported for enum values in PostgreSQL.
    
    Removing enum values is complex and risky because:
    1. Existing data might use these values
    2. PostgreSQL doesn't support removing enum values directly
    3. Would require creating a new enum type and migrating data
    
    If you need to remove these states, you must:
    1. Ensure no orders use these states
    2. Manually create a new enum without these values
    3. Migrate all data to the new enum
    4. Drop the old enum and rename the new one
    """
    # Note: PostgreSQL does not support removing enum values
    # This would require a complex migration involving:
    # 1. Creating a new enum type without these values
    # 2. Converting the column to the new type
    # 3. Dropping the old enum type
    # This is intentionally left as a no-op for safety
    pass
