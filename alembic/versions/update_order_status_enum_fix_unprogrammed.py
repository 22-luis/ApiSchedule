"""fix order status enum unprogrammed spelling and update values

Revision ID: fix_unprogrammed_enum
Revises: 53520c8b742b
Create Date: 2025-01-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fix_unprogrammed_enum'
down_revision: Union[str, Sequence[str], None] = '53520c8b742b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to fix unprogrammed spelling and update enum values."""
    
    # 1. Agregar los nuevos valores al enum si no existen
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'unprogrammed'")
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'programmed'")
    
    # 2. Actualizar registros existentes para corregir valores
    # Cambiar 'PENDING' a 'pending' (lowercase)
    op.execute("UPDATE \"order\" SET status = 'pending' WHERE status = 'PENDING'")
    
    # Cambiar 'PROGRAMADA' a 'programmed' 
    op.execute("UPDATE \"order\" SET status = 'programmed' WHERE status = 'PROGRAMADA'")
    
    # Cambiar 'IN_PROGRESS' a 'pending' (ya que eliminamos in_progress del flujo)
    op.execute("UPDATE \"order\" SET status = 'pending' WHERE status = 'IN_PROGRESS'")
    
    # Cambiar 'COMPLETED' a 'completed' (lowercase)
    op.execute("UPDATE \"order\" SET status = 'completed' WHERE status = 'COMPLETED'")
    
    # 3. Recrear el enum con los valores correctos
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_old")
    op.execute("CREATE TYPE orderstatus AS ENUM('pending', 'programmed', 'unprogrammed', 'completed')")
    op.execute("ALTER TABLE \"order\" ALTER COLUMN status TYPE orderstatus USING status::text::orderstatus")
    op.execute("DROP TYPE orderstatus_old")
    
    # 4. Actualizar el valor por defecto en la tabla
    op.execute("ALTER TABLE \"order\" ALTER COLUMN status SET DEFAULT 'unprogrammed'")


def downgrade() -> None:
    """Downgrade schema."""
    
    # Revertir a los valores anteriores
    op.execute("UPDATE \"order\" SET status = 'PENDING' WHERE status = 'pending'")
    op.execute("UPDATE \"order\" SET status = 'PROGRAMADA' WHERE status = 'programmed'")
    op.execute("UPDATE \"order\" SET status = 'PENDING' WHERE status = 'unprogrammed'")
    op.execute("UPDATE \"order\" SET status = 'COMPLETED' WHERE status = 'completed'")
    
    # Recrear el enum anterior
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_new")
    op.execute("CREATE TYPE orderstatus AS ENUM('PENDING', 'PROGRAMADA', 'IN_PROGRESS', 'COMPLETED')")
    op.execute("ALTER TABLE \"order\" ALTER COLUMN status TYPE orderstatus USING status::text::orderstatus")
    op.execute("DROP TYPE orderstatus_new")
    
    # Revertir el valor por defecto
    op.execute("ALTER TABLE \"order\" ALTER COLUMN status SET DEFAULT 'PENDING'")