from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.dependencies import get_current_user, require_roles
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserStateUpdate
from app.db.dependency import get_db
from typing import List, Optional
from app.models.team import Team
from app.models.state import UserState
from app.models.role import UserRole
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
    ):
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
def delete_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    past_state = db_user.state

    # The following assignments are correct for SQLAlchemy models, linter may show false positives
    db_user.username = user.username
    if user.password:
        db_user.password = hash_password(user.password)
    db_user.role = user.role
    db_user.state = user.state

    # Use .value for Enum comparisons to avoid linter errors
    if user.state.value == UserState.INACTIVE.value and past_state == UserState.ACTIVE:
        db_user.teams = []

    if user.teamIds is not None and user.state.value == UserState.ACTIVE.value:
        db_user.teams = db.query(Team).filter(Team.id.in_(user.teamIds)).all()

    db.commit()
    db.refresh(db_user)
    return db_user

@router.patch("/{user_id}/state", response_model=UserOut)
def update_user_state(user_id: str, state_update: UserStateUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.state = state_update.state
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[UserOut])
def get_users(
    db: Session = Depends(get_db), 
    state: Optional[UserState] = Query(default=None, description="State filter"),
    role: Optional[UserRole] = Query(default=None, description="Role filter"),
    skip: int = Query(0, ge=0, description="Skip"),
    limit: int = Query(10, ge=1, le=50, description="Limit"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
    ):
    query = db.query(User)
    if state is not None:
        query = query.filter(User.state == state)
    if role is not None:
        query = query.filter(User.role == role)
    users = query.all()
    return users

