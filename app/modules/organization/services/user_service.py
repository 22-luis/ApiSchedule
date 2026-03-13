import uuid
from typing import Optional, List, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.state import UserState
from app.modules.organization.repositories import user_repository, team_repository
from app.shared.utils.core.dependencies import ROLE_HIERARCHY
from app.shared.utils.security.security import hash_password

class UserService:
    @staticmethod
    def create_user(db: Session, user_data, current_user: User):
        """Crea un nuevo usuario validando permisos de jerarquía."""
        current_level = ROLE_HIERARCHY.get(current_user.role, 0)
        target_level = ROLE_HIERARCHY.get(user_data.role, 0)

        if current_level < target_level or (current_level == target_level and current_user.role != UserRole.ADMIN):
            raise HTTPException(
                status_code=403,
                detail=f"You don't have permission to create users with the role '{user_data.role.value}'"
            )

        if user_repository.find_by_username(db, user_data.username):
            raise HTTPException(status_code=400, detail="That name is already in use")
        
        db_user = User(
            username=user_data.username, 
            password=hash_password(user_data.password),
            role=user_data.role,
            full_name=user_data.full_name,
            cargo=user_data.cargo,
            document_name=user_data.document_name
        )
        return user_repository.save(db, db_user)

    @staticmethod
    def update_user(db: Session, target_user: User, user_update, current_user: User):
        """Actualiza un usuario protegiendo campos administrativos."""
        update_data = user_update.model_dump(exclude_unset=True)
        past_state = target_user.state

        # Protección de campos administrativos
        if current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
            for field in ["role", "state", "teamIds"]:
                update_data.pop(field, None)
        
        if "password" in update_data:
            password = update_data.pop("password")
            if password and password.strip():
                target_user.password = hash_password(password)

        if "teamIds" in update_data:
            team_ids = update_data.pop("teamIds")
            current_state = update_data.get("state", target_user.state)
            
            if current_state == UserState.ACTIVE:
                from app.modules.organization.models.team import Team
                target_user.teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
            else:
                target_user.teams = []

        if update_data.get("state") == UserState.INACTIVE and past_state == UserState.ACTIVE:
            target_user.teams = []

        if update_data:
            user_repository.update_selective(db, target_user.id, update_data)

        db.commit()
        db.refresh(target_user)
        return target_user

    @staticmethod
    def get_users_paged(db: Session, filters: dict):
        """Obtiene usuarios paginados."""
        skip = filters.pop("skip", 0)
        limit = filters.pop("limit", 10)
        
        total = user_repository.count_all(db, **filters)
        users = user_repository.find_all(db, skip=skip, limit=limit, **filters)
        return {"users": users, "total": total}
