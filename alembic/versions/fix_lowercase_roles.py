"""fix lowercase role values in users table

Revision ID: fix_lowercase_roles
Revises: dc283877710f
Create Date: 2026-01-08 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_lowercase_roles'
down_revision: Union[str, Sequence[str], None] = 'ebe052fa06aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix lowercase role values to uppercase."""
    # Update lowercase role values to uppercase
    role_mappings = [
        ('admin', 'ADMIN'),
        ('planner', 'PLANNER'),
        ('supervisor', 'SUPERVISOR'),
        ('timekeeper', 'TIMEKEEPER'),
        ('user', 'USER'),
        ('warehouse', 'WAREHOUSE'),
        ('accounting', 'ACCOUNTING'),
        ('qc_coordinator', 'QC_ENGINEER'),
        ('qc_assistant', 'QC_TECHNICIAN'),
    ]
    
    for old_val, new_val in role_mappings:
        op.execute(
            sa.text(f"UPDATE users SET role = '{new_val}' WHERE role = '{old_val}'")
        )


def downgrade() -> None:
    """Downgrade - convert back to lowercase (optional)."""
    # This is optional, you may choose not to revert
    pass
