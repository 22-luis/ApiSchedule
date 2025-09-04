"""fix_order_status_enum_migration

Revision ID: 26fa43a00a35
Revises: 7b4a4c283d75
Create Date: 2025-09-04 08:26:49.368170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26fa43a00a35'
down_revision: Union[str, Sequence[str], None] = '4ca9a42284bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix order status enum migration safely."""
    
    # 1. Primero, agregar una columna temporal para almacenar los valores convertidos
    op.add_column('order', sa.Column('status_temp', sa.String(50), nullable=True))
    
    # 2. Convertir los valores existentes a minúsculas en la columna temporal
    op.execute("""
        UPDATE "order" SET status_temp = CASE 
            WHEN status::text = 'PENDING' THEN 'pending'
            WHEN status::text = 'PROGRAMADA' THEN 'programmed'
            WHEN status::text = 'IN_PROGRESS' THEN 'pending'
            WHEN status::text = 'COMPLETED' THEN 'completed'
            WHEN status::text = 'pending' THEN 'pending'
            WHEN status::text = 'programmed' THEN 'programmed'
            WHEN status::text = 'completed' THEN 'completed'
            ELSE 'unprogrammed'
        END
    """)
    
    # 3. Eliminar la columna status original
    op.drop_column('order', 'status')
    
    # 4. Crear el nuevo enum con los valores correctos
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("CREATE TYPE orderstatus AS ENUM('pending', 'programmed', 'unprogrammed', 'completed')")
    
    # 5. Agregar la nueva columna status con el tipo enum
    op.add_column('order', sa.Column('status', sa.Enum('pending', 'programmed', 'unprogrammed', 'completed', name='orderstatus'), nullable=False, server_default='unprogrammed'))
    
    # 6. Copiar los valores de la columna temporal a la nueva columna status
    op.execute("UPDATE \"order\" SET status = status_temp::orderstatus")
    
    # 7. Eliminar la columna temporal
    op.drop_column('order', 'status_temp')


def downgrade() -> None:
    """Downgrade schema."""
    
    # 1. Agregar columna temporal
    op.add_column('order', sa.Column('status_temp', sa.String(50), nullable=True))
    
    # 2. Convertir valores a mayúsculas
    op.execute("""
        UPDATE "order" SET status_temp = CASE 
            WHEN status::text = 'pending' THEN 'PENDING'
            WHEN status::text = 'programmed' THEN 'PROGRAMADA'
            WHEN status::text = 'unprogrammed' THEN 'PENDING'
            WHEN status::text = 'completed' THEN 'COMPLETED'
            ELSE 'PENDING'
        END
    """)
    
    # 3. Eliminar columna status actual
    op.drop_column('order', 'status')
    
    # 4. Recrear enum anterior
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("CREATE TYPE orderstatus AS ENUM('PENDING', 'PROGRAMADA', 'IN_PROGRESS', 'COMPLETED')")
    
    # 5. Agregar columna status con enum anterior
    op.add_column('order', sa.Column('status', sa.Enum('PENDING', 'PROGRAMADA', 'IN_PROGRESS', 'COMPLETED', name='orderstatus'), nullable=False, server_default='PENDING'))
    
    # 6. Copiar valores
    op.execute("UPDATE \"order\" SET status = status_temp::orderstatus")
    
    # 7. Eliminar columna temporal
    op.drop_column('order', 'status_temp')
