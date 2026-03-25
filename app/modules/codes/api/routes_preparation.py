import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.modules.codes.schemas.preparation import PreparationCreate, PreparationOut
from app.modules.codes.services import preparation_service
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preparations", tags=["preparations"])


@router.post("/", response_model=PreparationOut)
def create_preparation(
    preparation: PreparationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER)),
):
    return preparation_service.create_preparation(db, preparation)
    

@router.get("/", response_model=List[PreparationOut])
def get_preparations(
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    ),
):
    return preparation_service.get_preparations(db)


@router.get("/{preparation_id}", response_model=PreparationOut)
def get_preparation(
    preparation_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR)
    ),
):
    return preparation_service.get_preparation_by_id(db, preparation_id)


@router.patch("/{preparation_id}", response_model=PreparationOut)
def update_preparation(
    preparation_id: str,
    preparation_update: PreparationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER)),
):
    return preparation_service.update_preparation(db, preparation_id, preparation_update)


@router.delete("/{preparation_id}")
def delete_preparation(
    preparation_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER)),
):
    return preparation_service.delete_preparation(db, preparation_id)