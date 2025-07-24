"""
Recrear el tipo ENUM orderstatus con valores en minúsculas y migrar los datos

Revision ID: e4fd39ab5b1f
Revises: c46df6df72ae
Create Date: 2024-07-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e4fd39ab5b1f'
down_revision = 'c46df6df72ae'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Crear el nuevo tipo ENUM en minúsculas
    op.execute("CREATE TYPE orderstatus_new AS ENUM ('pending', 'programada', 'in_progress', 'completed')")
    # 2. Agregar columna temporal como VARCHAR
    op.execute('ALTER TABLE "order" ADD COLUMN status_tmp VARCHAR;')
    # 3. Copiar valores actuales a la columna temporal, mapeando a minúsculas
    op.execute("UPDATE \"order\" SET status_tmp = LOWER(status::text);")
    # 4. Eliminar columna original
    op.execute('ALTER TABLE "order" DROP COLUMN status;')
    # 5. Agregar columna con el nuevo ENUM
    op.execute('ALTER TABLE "order" ADD COLUMN status orderstatus_new;')
    # 6. Copiar valores de la temporal a la nueva columna ENUM
    op.execute('UPDATE "order" SET status = status_tmp::orderstatus_new;')
    # 7. Eliminar columna temporal
    op.execute('ALTER TABLE "order" DROP COLUMN status_tmp;')
    # 8. Eliminar el tipo ENUM viejo y renombrar el nuevo
    op.execute('DROP TYPE orderstatus;')
    op.execute('ALTER TYPE orderstatus_new RENAME TO orderstatus;')

def downgrade():
    pass
