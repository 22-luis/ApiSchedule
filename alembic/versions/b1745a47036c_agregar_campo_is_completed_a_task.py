"""Agregar campo is_completed a Task

Revision ID: b1745a47036c
Revises: 3096d60d88d7
Create Date: 2025-09-26 12:03:26.565478

"""
from alembic import op
import sqlalchemy as sa

# Revisión Alembic
revision = "b1745a47036c"
down_revision = "3096d60d88d7"
branch_labels = None
depends_on = None

# Nuevo ENUM con todos los valores correctos
new_orderstatus = sa.Enum(
    "pending",
    "programmed",
    "unprogrammed",
    "manufactured",
    "delivered",
    "completed",
    "not_programmable",
    name="orderstatus"
)

# Viejo ENUM (sin not_programmable)
old_orderstatus = sa.Enum(
    "pending",
    "programmed",
    "unprogrammed",
    "manufactured",
    "delivered",
    "completed",
    name="orderstatus_old"
)


def upgrade():
    # 1️⃣ Agregar campo is_completed en task
    op.add_column("task", sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"))

    # 2️⃣ Manejo de ENUM en order.status
    # Renombrar el ENUM viejo
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_old")

    # Crear el nuevo ENUM con todos los valores
    new_orderstatus.create(op.get_bind(), checkfirst=False)

    # Alterar la columna para usar el nuevo ENUM
    op.alter_column(
        "order",
        "status",
        type_=new_orderstatus,
        postgresql_using="status::text::orderstatus"
    )

    # Borrar el ENUM viejo
    old_orderstatus.drop(op.get_bind(), checkfirst=False)


def downgrade():
    # Revertir cambios

    # 1️⃣ Quitar columna is_completed
    op.drop_column("task", "is_completed")

    # 2️⃣ Revertir ENUM
    op.execute("ALTER TYPE orderstatus RENAME TO orderstatus_new")

    old_orderstatus.create(op.get_bind(), checkfirst=False)

    op.alter_column(
        "order",
        "status",
        type_=old_orderstatus,
        postgresql_using="status::text::orderstatus_old"
    )

    new_orderstatus.drop(op.get_bind(), checkfirst=False)

    op.execute("ALTER TYPE orderstatus_new RENAME TO orderstatus")
