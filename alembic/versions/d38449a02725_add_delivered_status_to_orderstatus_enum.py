"""add_delivered_status_to_orderstatus_enum

Revision ID: d38449a02725
Revises: 972dddab1a86
Create Date: 2025-09-04 11:01:24.743563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd38449a02725'
down_revision: Union[str, Sequence[str], None] = '972dddab1a86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Agregar el nuevo valor 'delivered' al enum orderstatus
    op.execute("ALTER TYPE orderstatus ADD VALUE 'delivered'")


def downgrade() -> None:
    """Downgrade schema."""
    # No se puede eliminar un valor de un enum en PostgreSQL de forma directa
    # Se requeriría recrear el enum completo, lo cual es complejo
    # Por simplicidad, dejamos el valor en el enum
    pass
