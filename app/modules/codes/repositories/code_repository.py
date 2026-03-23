import uuid
from typing import Optional, List, Tuple

from sqlalchemy import func, cast, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session

from app.modules.codes.models.code import Code
from app.modules.orders.models.order import Order
from app.modules.quality.models.catalog_test import CatalogTest
from app.modules.quality.models.code_test import CodeTest
from app.shared.core.enums import WeighingActivities, ManufacturingActivities


def find_by_id(db: Session, code_id: uuid.UUID) -> Optional[Code]:
    """Devuelve un Code por su UUID, o None si no existe."""
    return db.query(Code).filter(Code.id == code_id).first()


def find_all(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> Tuple[List[Code], int]:
    """Lista paginada de todos los codes. Devuelve (registros, total)."""
    query = db.query(Code)
    if search:
        pattern = f"%{search.lower()}%"
        query = query.filter(
            Code.code.ilike(pattern) | Code.description.ilike(pattern)
        )
    total = query.count()
    codes = query.order_by(Code.code).offset(skip).limit(limit).all()
    return codes, total


def find_all_no_filter(db: Session) -> List[Code]:
    """Devuelve todos los codes sin paginación (usado en bulk operations)."""
    return db.query(Code).all()


def find_by_code_and_activity(
    db: Session, code: str, activity: str
) -> Optional[Code]:
    """Busca un Code por el par (code, activity)."""
    return db.query(Code).filter(Code.code == code, Code.activity == activity).first()


def find_by_code(db: Session, code: str) -> List[Code]:
    """Devuelve todos los codes que comparten el mismo código."""
    return db.query(Code).filter(Code.code == code).all()


def find_production_codes(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> Tuple[List[Code], int]:
    """
    Lista paginada de codes con actividades productivas (un registro por código único).
    Devuelve (registros, total).
    """
    production_activities = [
        WeighingActivities.PESADO,
        ManufacturingActivities.FABRICACION,
        ManufacturingActivities.MOL_PASTA,
        ManufacturingActivities.MOL_POLVO,
        ManufacturingActivities.MEZ_MAQUINA,
        ManufacturingActivities.MEZ_POLVO,
        ManufacturingActivities.MEZ_LIQUIDA,
    ]

    subquery = db.query(
        func.min(cast(Code.id, String)).cast(UUID).label("min_id")
    ).filter(Code.activity.in_(production_activities))

    if search:
        pattern = f"%{search.lower()}%"
        subquery = subquery.filter(
            Code.code.ilike(pattern) | Code.description.ilike(pattern)
        )

    subquery = subquery.group_by(Code.code).subquery()
    query = db.query(Code).filter(Code.id.in_(db.query(subquery.c.min_id)))

    total = query.count()
    codes = query.order_by(Code.code).offset(skip).limit(limit).all()
    return codes, total


def find_tests_for_codes(
    db: Session, code_ids: List[uuid.UUID]
) -> List[Tuple[uuid.UUID, CatalogTest]]:
    """Devuelve los pares (code_id, CatalogTest) para una lista de IDs."""
    if not code_ids:
        return []
    return (
        db.query(CodeTest.code_id, CatalogTest)
        .join(CatalogTest, CatalogTest.id == CodeTest.catalog_test_id)
        .filter(CodeTest.code_id.in_(code_ids))
        .all()
    )


def find_lotes_by_code(db: Session, code: str) -> List[str]:
    """Devuelve la lista de lotes activos para un código."""
    rows = db.query(Order.lote).filter(
        Order.code == code,
        Order.status != "completed",
    ).all()
    return [r[0] for r in rows if r[0] is not None]


def save(db: Session, code: Code, flush: bool = False) -> Code:
    db.add(code)
    if flush:
        db.flush()
    else:
        db.commit()
        db.refresh(code)
    return code


def delete(db: Session, code: Code) -> None:
    db.delete(code)


def commit(db: Session) -> None:
    db.commit()
