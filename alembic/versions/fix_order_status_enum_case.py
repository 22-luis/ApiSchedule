"""
Migración Alembic para corregir los valores de la columna status en la tabla order.
Convierte los valores en mayúsculas a minúsculas para que coincidan con el Enum del modelo OrderStatus.
"""
from alembic import op
import sqlalchemy as sa

# Reemplaza estos valores con los de tu entorno si es necesario
description = 'Corrige los valores de status en la tabla order para que sean minúsculas.'

# revision identifiers, used by Alembic.
revision = 'fix_order_status_enum_case'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Actualiza los valores en mayúsculas a minúsculas
    op.execute("""
        UPDATE "order" SET status = 'pending' WHERE status = 'PENDING';
        UPDATE "order" SET status = 'in_progress' WHERE status = 'IN_PROGRESS';
        UPDATE "order" SET status = 'completed' WHERE status = 'COMPLETED';
        UPDATE "order" SET status = 'programada' WHERE status = 'PROGRAMADA';
    """)

def downgrade():
    # Revierte los cambios a mayúsculas
    op.execute("""
        UPDATE "order" SET status = 'PENDING' WHERE status = 'pending';
        UPDATE "order" SET status = 'IN_PROGRESS' WHERE status = 'in_progress';
        UPDATE "order" SET status = 'COMPLETED' WHERE status = 'completed';
        UPDATE "order" SET status = 'PROGRAMADA' WHERE status = 'programada';
    """) 