import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.organization.models.user import User

def find_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """Busca un usuario por su ID (UUID)."""
    return db.query(User).filter(User.id == user_id).first()

def find_by_username(db: Session, username: str) -> Optional[User]:
    """Busca un usuario por su nombre de usuario (username)."""
    return db.query(User).filter(User.username == username).first()

def find_all(
    db: Session,
    state=None,
    role=None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 10
) -> List[User]:
    """Busca usuarios con filtros y paginación."""
    query = db.query(User)
    if state is not None:
        query = query.filter(User.state == state)
    if role is not None:
        query = query.filter(User.role == role)
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()

def count_all(
    db: Session,
    state=None,
    role=None,
    search: Optional[str] = None
) -> int:
    """Cuenta el total de usuarios que coinciden con los filtros."""
    query = db.query(User)
    if state is not None:
        query = query.filter(User.state == state)
    if role is not None:
        query = query.filter(User.role == role)
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))
    return query.count()

def save(db: Session, user: User) -> User:
    """Guarda o actualiza un usuario en la BD."""
    db.add(user)
    db.commit()
    return user

def delete(db: Session, user: User) -> None:
    """Elimina un usuario de la BD."""
    db.delete(user)
    db.commit()

def update_selective(db: Session, user_id: uuid.UUID, update_data: dict) -> None:
    """Realiza una actualización selectiva directamente en la BD."""
    db.query(User).filter(User.id == user_id).update(update_data)
    db.commit()
