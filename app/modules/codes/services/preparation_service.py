import logging
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.codes.models.preparation import Preparation
from app.modules.codes.repositories import preparation_repository
from app.modules.codes.schemas.preparation import PreparationCreate, PreparationOut
from app.shared.utils.business.data_cleaning import clean_int, clean_str

logger = logging.getLogger(__name__)


def create_preparation(db: Session, preparation_data: PreparationCreate) -> Preparation:
    db_preparation = Preparation(**preparation_data.model_dump())
    return preparation_repository.save(db, db_preparation)


def get_preparations(db: Session) -> List[PreparationOut]:
    preparations = preparation_repository.find_all(db)
    return [PreparationOut.model_validate(p) for p in preparations]


def get_preparation_by_id(db: Session, preparation_id: str) -> Preparation:
    preparation = preparation_repository.find_by_id(db, preparation_id)
    if not preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    return preparation


def update_preparation(
    db: Session, preparation_id: str, preparation_update: PreparationCreate
) -> Preparation:
    db_preparation = preparation_repository.find_by_id(db, preparation_id)
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    
    for field, value in preparation_update.model_dump(exclude_unset=True).items():
        setattr(db_preparation, field, value)
    
    preparation_repository.commit(db)
    db.refresh(db_preparation)
    return db_preparation


def delete_preparation(db: Session, preparation_id: str) -> dict:
    db_preparation = preparation_repository.find_by_id(db, preparation_id)
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    
    preparation_repository.delete(db, db_preparation)
    preparation_repository.commit(db)
    return {"message": "Preparation deleted successfully"}
