import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.modules.core.models.role import UserRole
from app.modules.core.models.state import UserState
from app.modules.core.models.team import Team
from app.modules.core.models.user import User
from app.modules.core.schemas.user import UserCreate, UserUpdate, UserOut, UsersPageOut, UserStateUpdate
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user, require_roles, ROLE_HIERARCHY, \
    check_user_modification_permission
from app.shared.utils.security.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserOut)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    current_level = ROLE_HIERARCHY.get(_current_user.role, 0)
    target_level = ROLE_HIERARCHY.get(user.role, 0)

    if current_level < target_level or (current_level == target_level and _current_user.role != UserRole.ADMIN):
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
        role=user.role,
        full_name=user.full_name,
        cargo=user.cargo,
        document_name=user.document_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserOut.model_validate(db_user)

@router.delete("/{user_id}")
def delete_user(
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db.delete(target_user)
    db.commit()
    return {"message": "User deleted successfully"}

@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_update: UserUpdate, 
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission), 
    _current_user: User = Depends(get_current_user)
):
    update_data = user_update.model_dump(exclude_unset=True)
    past_state = target_user.state

    # Protección de campos administrativos para usuarios sin privilegios
    if _current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
        # Si no es admin/planner, eliminar campos restringidos del update_data
        for field in ["role", "state", "teamIds"]:
            update_data.pop(field, None)
    
    # Asegurar que campos de perfil siempre se permitan si vienen en el payload
    profile_fields = ["full_name", "cargo", "document_name"]

    # Procesar campos especiales
    if "password" in update_data:
        password = update_data.pop("password")
        if password and password.strip():
            target_user.password = hash_password(password)

    if "teamIds" in update_data:
        team_ids = update_data.pop("teamIds")
        if "state" in update_data:
            current_state = update_data["state"]
        else:
            current_state = target_user.state
            
        if current_state.value == UserState.ACTIVE.value:
            target_user.teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        else:
            target_user.teams = []

    # Manejar cambio a INACTIVE (limpiar equipos)
    if update_data.get("state") == UserState.INACTIVE and past_state == UserState.ACTIVE:
        target_user.teams = []

    # Actualizar campos directamente en la base de datos para asegurar persistencia
    if update_data:
        db.query(User).filter(User.id == target_user.id).update(update_data)

    db.commit()
    db.refresh(target_user)
    
    return UserOut.model_validate(target_user)

@router.patch("/{user_id}/state", response_model=UserOut)
def update_user_state(
    state_update: UserStateUpdate, 
    db: Session = Depends(get_db), 
    target_user: User = Depends(check_user_modification_permission), 
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
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
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
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
    
    return UsersPageOut(
        users=[UserOut.model_validate(user) for user in users],
        total=total
    )

@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserOut.model_validate(user)

@router.get("/{user_id}/signature", response_model=UserOut)
def get_user_signature(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "id": user.id,
        "signature": user.signature,
        "document_name": user.document_name
    }
