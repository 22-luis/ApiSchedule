"""update_user_role_enum

Revision ID: 3332f46ab036
Revises: 7306f82f6078
Create Date: 2026-01-12 11:42:28.775204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3332f46ab036'
down_revision: Union[str, Sequence[str], None] = '7306f82f6078'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Renaming ENUM values requires database-specific commands.
    # For PostgreSQL, we need to add the new values first.
    
    # We need to execute COMMIT because ALTER TYPE ADD VALUE cannot run in a transaction block
    op.execute("COMMIT")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'QC_COORDINATOR'")
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'QC_ASSISTANT'")
    
    # 1. Update existing data to avoid constraint violations if possible
    op.execute("UPDATE users SET role = 'QC_COORDINATOR' WHERE role = 'QC_ENGINEER'")
    op.execute("UPDATE users SET role = 'QC_ASSISTANT' WHERE role = 'QC_TECHNICIAN'")

def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE users SET role = 'QC_ENGINEER' WHERE role = 'QC_COORDINATOR'")
    op.execute("UPDATE users SET role = 'QC_TECHNICIAN' WHERE role = 'QC_ASSISTANT'")

