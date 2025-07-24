"""
Migrar orderstatus enum a minúsculas

Revision ID: 0d98ef180ba7
Revises: c9150309f325
Create Date: 2024-07-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0d98ef180ba7'
down_revision = 'c9150309f325'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Crear el nuevo tipo ENUM
    op.execute("CREATE TYPE orderstatus_new AS ENUM ('pending', 'programada', 'in_progress', 'completed')")
    # 2. Agregar columna temporal como VARCHAR
    op.execute('ALTER TABLE "order" ADD COLUMN status_tmp VARCHAR;')
    # 3. Copiar valores actuales a la columna temporal, mapeando a minúsculas
    op.execute("UPDATE \"order\" SET status_tmp = CASE status::text WHEN 'PENDING' THEN 'pending' WHEN 'PROGRAMADA' THEN 'programada' WHEN 'IN_PROGRESS' THEN 'in_progress' WHEN 'COMPLETED' THEN 'completed' ELSE LOWER(status::text) END;")
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
    # No implementado (sería el proceso inverso)
    pass 