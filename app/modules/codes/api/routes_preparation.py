from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.modules.codes.models.preparation import Preparation
from app.modules.codes.schemas.preparation import PreparationCreate, PreparationOut
from app.shared.db.session import get_db
from app.modules.core.models.user import User
from app.shared.utils.core.dependencies import require_roles
from app.modules.core.models.role import UserRole
from app.shared.utils.business.data_cleaning import clean_int, clean_str

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

@router.post("/bulk_upload")
def bulk_upload_preparations(preparations: list[dict], db: Session = Depends(get_db), current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    created = 0
    updated = 0
    errors = []
    
    for idx, prep_data in enumerate(preparations):
        description = clean_str(prep_data.get("description"))
        minutes = clean_int(prep_data.get("minutes"))
        
        if not description or minutes is None:
            errors.append({"row": idx+1, "error": "Falta descripción o minutos"})
            continue
        
        # Buscar si existe una preparación con la misma descripción
        existing_prep = db.query(Preparation).filter(Preparation.description == description).first()
        
        if existing_prep:
            # Si existe, actualizar solo si los minutos han cambiado
            if existing_prep.minutes != minutes:
                existing_prep.minutes = minutes
                updated += 1
        else:
            # Si no existe, crear nueva
            db_prep = Preparation(
                description=description,
                minutes=minutes
            )
            db.add(db_prep)
            created += 1
    
    db.commit()
    
    total_processed = len(preparations) - len(errors)
    unchanged = total_processed - created - updated
    
    return {
        "created": created, 
        "updated": updated, 
        "unchanged": unchanged,
        "errors": errors,
        "total_processed": total_processed
    }

@router.get("/", response_model=List[PreparationOut])
def get_preparations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    preparations = db.query(Preparation).all()
    return [PreparationOut.model_validate(p) for p in preparations]

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