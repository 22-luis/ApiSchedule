import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.organization.schemas.user import UserCreate, UserUpdate, UserOut, UsersPageOut
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user, require_roles, check_user_modification_permission
from app.modules.organization.services.user_service import UserService
from app.modules.organization.repositories import user_repository

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    db_user = UserService.create_user(db, user, current_user)
    return UserOut.model_validate(db_user)

@router.delete("/{user_id}")
def delete_user(
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    user_repository.delete(db, target_user)
    return {"message": "User deleted successfully"}

@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_update: UserUpdate, 
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission), 
    current_user: User = Depends(get_current_user)
):
    updated_user = UserService.update_user(db, target_user, user_update, current_user)
    return UserOut.model_validate(updated_user)

@router.get("/", response_model=UsersPageOut)
def get_users(
    db: Session = Depends(get_db), 
    role: Optional[UserRole] = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    filters = {"role": role, "search": search, "skip": skip, "limit": limit}
    result = UserService.get_users_paged(db, filters)
    return UsersPageOut(
        users=[UserOut.model_validate(u) for u in result["users"]],
        total=result["total"]
    )

@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = user_repository.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)

@router.get("/{user_id}/signature")
def get_user_signature(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = user_repository.find_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "signature": user.signature
    }
