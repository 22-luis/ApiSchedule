from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.models.preparation import Preparation
from app.schemas.preparation import PreparationCreate, PreparationOut
from app.db.dependency import get_db
from app.models.user import User
from app.utils.dependencies import require_roles
from app.models.role import UserRole

router = APIRouter(prefix="/preparations", tags=["preparations"])

@router.post("/", response_model=PreparationOut)
def create_preparation(
    preparation: PreparationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_preparation = Preparation(**preparation.dict())
    db.add(db_preparation)
    db.commit()
    db.refresh(db_preparation)
    return db_preparation

@router.get("/", response_model=List[PreparationOut])
def get_preparations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return db.query(Preparation).all()

@router.get("/{preparation_id}", response_model=PreparationOut)
def get_preparation(
    preparation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    preparation = db.query(Preparation).filter(Preparation.id == preparation_id).first()
    if not preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    return preparation

@router.patch("/{preparation_id}", response_model=PreparationOut)
def update_preparation(
    preparation_id: str,
    preparation_update: PreparationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_preparation = db.query(Preparation).filter(Preparation.id == preparation_id).first()
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    for field, value in preparation_update.dict(exclude_unset=True).items():
        setattr(db_preparation, field, value)
    db.commit()
    db.refresh(db_preparation)
    return db_preparation

@router.delete("/{preparation_id}")
def delete_preparation(
    preparation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_preparation = db.query(Preparation).filter(Preparation.id == preparation_id).first()
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    db.delete(db_preparation)
    db.commit()
    return {"message": "Preparation deleted successfully"} 