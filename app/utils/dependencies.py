from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.dependency import get_db
from app.models.user import User
from app.models.role import UserRole
from app.utils.jwt import decode_token
from app.utils.security import oauth2_scheme

# 1. Centralizar la jerarquía de roles en un solo lugar.
# Esto evita la duplicación en `routes_user.py` y en otras funciones de este archivo.
ROLE_HIERARCHY = {
    UserRole.ADMIN: 4,
    UserRole.PLANNER: 3,
    UserRole.ACCOUNTING: 3,
    UserRole.SUPERVISOR: 2,
    UserRole.WAREHOUSE: 1,
    UserRole.USER: 0,
}

def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def require_roles(*roles: List[UserRole]):
    flat_roles = []
    for r in roles:
        if isinstance(r, (list, tuple)):
            flat_roles.extend(r)
        else:
            flat_roles.append(r)
    
    def role_checker(current_user=Depends(get_current_user)):
        current_level = ROLE_HIERARCHY.get(current_user.role, 0)
        
        # Obtener el nivel mínimo requerido de los roles pasados
        min_required_level = min(ROLE_HIERARCHY.get(role, 99) for role in flat_roles)
        
        if current_level >= min_required_level:
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action",
        )
    return role_checker


# 2. Crear una dependencia para obtener el usuario objetivo y manejar el 404.
def get_target_user(user_id: str, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# 3. Convertir la verificación de permisos en una dependencia real.
def check_user_modification_permission(
    current_user: User = Depends(get_current_user),
    target_user: User = Depends(get_target_user)
):
    current_level = ROLE_HIERARCHY.get(current_user.role, 0)
    target_level = ROLE_HIERARCHY.get(target_user.role, 0)

    # Un admin puede modificar a cualquiera (excepto a sí mismo en ciertos casos, pero eso se maneja en la ruta).
    if current_user.role == UserRole.ADMIN:
        return target_user

    # Permitir que un usuario edite su propia información
    if current_user.id == target_user.id:
        return target_user

    if current_level <= target_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar usuarios con rol igual o superior al tuyo.",
        )
    
    return target_user
