from typing import Optional, List

from sqlalchemy.orm import Session

from app.modules.codes.models.preparation import Preparation


def find_by_id(db: Session, preparation_id: str) -> Optional[Preparation]:
    """Devuelve una Preparation por ID, o None si no existe."""
    return db.query(Preparation).filter(Preparation.id == preparation_id).first()


def find_all(db: Session) -> List[Preparation]:
    """Devuelve todas las preparaciones."""
    return db.query(Preparation).all()


def save(db: Session, preparation: Preparation, flush: bool = False) -> Preparation:
    """Persiste una Preparation (add + commit/flush + refresh)."""
    db.add(preparation)
    if flush:
        db.flush()
    else:
        db.commit()
        db.refresh(preparation)
    return preparation


def delete(db: Session, preparation: Preparation) -> None:
    """Marca una Preparation para borrar (el commit lo hace el servicio)."""
    db.delete(preparation)


def commit(db: Session) -> None:
    """Hace commit en la sesión."""
    db.commit()
