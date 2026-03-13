from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.modules.organization.repositories import user_repository
from app.shared.utils.security.jwt import create_access_token
from app.shared.utils.security.security import verify_password

class AuthService:
    @staticmethod
    def login(db: Session, username: str, password: str):
        """Autentica a un usuario y genera un token JWT."""
        user = user_repository.find_by_username(db, username)
        if not user or not user.password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Incorrect username or password"
            )
        
        try:
            if not verify_password(password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Incorrect username or password"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Incorrect username or password"
            )

        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username, "role": user.role.value}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "teamIds": user.active_team_ids
            }
        }
