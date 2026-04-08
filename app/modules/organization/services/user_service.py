import uuid
from typing import Optional, List, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.programming.models.programming import ProgrammingTask
from app.modules.programming.models.task import Task
from app.modules.organization.models.team import Team
from app.modules.organization.models.user import User
from app.modules.organization.models.user_profile import UserProfile
from app.modules.organization.models.role import UserRole
from app.modules.organization.repositories import user_repository, team_repository
from app.shared.utils.core.dependencies import ROLE_HIERARCHY
from app.shared.utils.security.security import hash_password



class UserService:

    @staticmethod
    def create_user(db: Session, user_data, current_user: User):
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
        )
        db.add(db_user)
        db.flush()  # get db_user.id without committing

        db_profile = UserProfile(
            user_id=db_user.id,
            role=user_data.role,
            full_name=user_data.full_name,
            cargo=user_data.cargo,
        )
        db.add(db_profile)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user(db: Session, target_user: User, user_update, current_user: User):
        update_data = user_update.model_dump(exclude_unset=True)

        # Protección de campos administrativos
        if current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
            for field in ["role", "teamIds"]:
                update_data.pop(field, None)

        if "password" in update_data:
            password = update_data.pop("password")
            if password and password.strip():
                target_user.password = hash_password(password)

        if "teamIds" in update_data:
            team_ids = update_data.pop("teamIds")
            from app.modules.organization.models.team import Team
            target_user.teams = db.query(Team).filter(Team.id.in_(team_ids)).all()

        # Fields that belong to UserProfile
        PROFILE_FIELDS = {"full_name", "cargo", "role", "signature"}
        profile_data = {k: v for k, v in update_data.items() if k in PROFILE_FIELDS}
        user_data = {k: v for k, v in update_data.items() if k not in PROFILE_FIELDS}

        if profile_data:
            if target_user.profile is None:
                # Create profile on the fly if missing (should not happen normally)
                target_user.profile = UserProfile(user_id=target_user.id)
                db.add(target_user.profile)
                db.flush()
            for field, value in profile_data.items():
                setattr(target_user.profile, field, value)

        if user_data:
            user_repository.update_selective(db, target_user.id, user_data)

        db.commit()
        db.refresh(target_user)
        return target_user

    @staticmethod
    def get_users_paged(db: Session, filters: dict):
        skip = filters.pop("skip", 0)
        limit = filters.pop("limit", 10)

        total = user_repository.count_all(db, **filters)
        users = user_repository.find_all(db, skip=skip, limit=limit, **filters)
        return {"users": users, "total": total}

    @staticmethod
    def find_by_id(db: Session, user_id: uuid.UUID):
        return user_repository.find_by_id(db, user_id)

    @staticmethod
    def delete_user(db: Session, target_user: User):
        uid = target_user.id

        db.query(ProgrammingTask).filter(
            ProgrammingTask.completed_by_user_id == uid
        ).update({ProgrammingTask.completed_by_user_id: None}, synchronize_session=False)

        db.query(Task).filter(
            Task.created_by_user_id == uid
        ).update({Task.created_by_user_id: None}, synchronize_session=False)

        db.query(Team).filter(
            Team.supervisorId == uid
        ).update({Team.supervisorId: None}, synchronize_session=False)

        user_repository.delete(db, target_user)

