from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.orders.schemas.special_code import SpecialCode, SpecialCodeCreate, SpecialCodeUpdate
from app.modules.orders.services.special_code_service import SpecialCodeService

router = APIRouter(prefix="/orders/special-codes", tags=["orders"])

@router.get("/", response_model=List[SpecialCode])
def get_special_codes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return SpecialCodeService.get_all(db, skip=skip, limit=limit)

@router.post("/", response_model=SpecialCode)
def create_special_code(
    special_code_in: SpecialCodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    return SpecialCodeService.create(db, special_code_in)

@router.put("/{special_code_id}", response_model=SpecialCode)
def update_special_code(
    special_code_id: str,
    special_code_in: SpecialCodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    return SpecialCodeService.update(db, special_code_id, special_code_in)

@router.delete("/{special_code_id}")
def delete_special_code(
    special_code_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    SpecialCodeService.delete(db, special_code_id)
    return {"message": "Excepción eliminada correctamente"}
