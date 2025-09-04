from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependency import get_db
from app.models.user import User
from app.utils.jwt import decode_token
from app.utils.security import oauth2_scheme


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


def require_roles(*roles):
    # Aplanar roles en caso de que se pase una lista (por ejemplo, require_roles(["admin", "planner"]))
    flat_roles = []
    for r in roles:
        if isinstance(r, (list, tuple)):
            flat_roles.extend(r)
        else:
            flat_roles.append(r)

    def role_checker(current_user=Depends(get_current_user)):
        # Permitir jerarquía: ADMIN > PLANNER > SUPERVISOR > WAREHOUSE > USER
        hierarchy = {
            "admin": 4,
            "planner": 3,
            "supervisor": 2,
            "warehouse": 1,
            "user": 0,
        }
        user_role = str(
            current_user.role.value
            if hasattr(current_user.role, "value")
            else current_user.role
        )
        # Convertir todos los roles requeridos a string simple (por ejemplo, 'admin')
        required_roles = [
            str(role.value) if hasattr(role, "value") else str(role)
            for role in flat_roles
        ]
        if any(hierarchy[user_role] >= hierarchy[role] for role in required_roles):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action",
        )

    return role_checker


def check_user_permission_for_target_user(current_user: User, target_user: User):
    """
    Verifica si el usuario actual puede modificar al usuario objetivo.
    Un usuario no puede modificar a otro usuario con rol igual o superior.
    """
    hierarchy = {"admin": 4, "planner": 3, "supervisor": 2, "warehouse": 1, "user": 0}

    current_user_role = str(
        current_user.role.value
        if hasattr(current_user.role, "value")
        else current_user.role
    )
    target_user_role = str(
        target_user.role.value
        if hasattr(target_user.role, "value")
        else target_user.role
    )

    current_level = hierarchy.get(current_user_role, 0)
    target_level = hierarchy.get(target_user_role, 0)

    if current_level <= target_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot modify users with equal or higher role than yours",
        )

    return True
