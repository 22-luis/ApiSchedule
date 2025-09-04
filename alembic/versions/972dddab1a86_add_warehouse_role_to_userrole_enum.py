"""add_warehouse_role_to_userrole_enum

Revision ID: 972dddab1a86
Revises: f6dab950833f
Create Date: 2025-09-04 10:23:17.993627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '972dddab1a86'
down_revision: Union[str, Sequence[str], None] = 'f6dab950833f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add WAREHOUSE value to the userrole enum
    op.execute("ALTER TYPE userrole ADD VALUE 'WAREHOUSE'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values directly
    # This would require recreating the enum and updating all references
    # For now, we'll leave this as a no-op since removing enum values
    # is complex and potentially destructive
    pass
