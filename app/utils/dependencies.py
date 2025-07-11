from fastapi import Depends, HTTPException, status
from jose import JWTError
from app.models.role import UserRole
from sqlalchemy.orm import Session
from app.utils.jwt import decode_token
from app.db.dependency import get_db
from app.models.user import User
from app.utils.security import oauth2_scheme

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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
    def role_checker(current_user=Depends(get_current_user)):
        # Permitir jerarquía: ADMIN > PLANNER > SUPERVISOR > USER
        hierarchy = {
            UserRole.ADMIN: 3,
            UserRole.PLANNER: 2,
            UserRole.SUPERVISOR: 1,
            UserRole.USER: 0
        }
        user_role = current_user.role
        # Si el rol requerido es menor o igual al del usuario, permitir
        if any(hierarchy[user_role] >= hierarchy[role] for role in roles):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action"
        )
    return role_checker