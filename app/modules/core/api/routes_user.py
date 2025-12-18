import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.modules.core.models.user import User
from app.modules.core.models.role import UserRole
from app.modules.core.models.team import Team
from app.modules.core.models.state import UserState
from app.modules.core.schemas.user import UserCreate, UserUpdate, UserOut, UsersPageOut, UserStateUpdate
from app.shared.utils.core.dependencies import get_current_user, require_roles, ROLE_HIERARCHY, check_user_modification_permission
from app.shared.utils.security.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    current_level = ROLE_HIERARCHY.get(current_user.role, 0)
    target_level = ROLE_HIERARCHY.get(user.role, 0)

    if current_level < target_level or (current_level == target_level and current_user.role != UserRole.ADMIN):
        raise HTTPException(
            status_code=403,
            detail=f"You don't have permission to create users with the role '{user.role.value}'"
        )

    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="That name is already in use")
    
    db_user = User(
        username=user.username, 
        password=hash_password(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/{user_id}")
def delete_user(
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db.delete(target_user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user: UserUpdate, 
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission), 
    current_user: User = Depends(get_current_user())
):
    past_state = target_user.state

    setattr(target_user, "username", user.username)
    setattr(target_user, "signature", user.signature)
    if user.password is not None and user.password.strip():
        setattr(target_user, "password", hash_password(user.password))
    setattr(target_user, "role", user.role)
    setattr(target_user, "state", user.state)

    if user.state.value == UserState.INACTIVE.value and past_state.value == UserState.ACTIVE.value:
        target_user.teams = []

    if user.teamIds is not None and user.state.value == UserState.ACTIVE.value:
        target_user.teams = db.query(Team).filter(Team.id.in_(user.teamIds)).all()

    db.commit()
    db.refresh(target_user)
    return target_user

@router.patch("/{user_id}/state", response_model=UserOut)
def update_user_state(
    state_update: UserStateUpdate, 
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    setattr(target_user, "state", state_update.state)
    db.commit()
    db.refresh(target_user)
    return target_user

@router.get("/", response_model=UsersPageOut)
def get_users(
    db: Session = Depends(get_db), 
    state: Optional[UserState] = Query(default=None, description="State filter"),
    role: Optional[UserRole] = Query(default=None, description="Role filter"),
    skip: int = Query(0, ge=0, description="Skip"),
    limit: int = Query(10, ge=1, le=50, description="Limit"),
    search: Optional[str] = Query(None, description="Search by username"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    query = db.query(User)
    if state is not None:
        query = query.filter(User.state == state)
    if role is not None:
        query = query.filter(User.role == role)
    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    result = []
    for user in users:
        team_ids = [team.id for team in getattr(user, 'teams', [])]
        result.append({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "state": user.state,
            "teamIds": team_ids
        })
    return {"users": result, "total": total}

@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/{user_id}/signature", response_model=UserOut)
def get_user_signature(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"signature": user.signature}
