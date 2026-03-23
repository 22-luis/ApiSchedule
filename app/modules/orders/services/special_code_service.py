from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException
from app.modules.orders.models.special_code import SpecialCode
from app.modules.orders.repositories import special_code_repository
from app.modules.orders.schemas.special_code import SpecialCodeCreate, SpecialCodeUpdate

class SpecialCodeService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[SpecialCode]:
        return special_code_repository.find_all(db, skip=skip, limit=limit)

    @staticmethod
    def create(db: Session, special_code_in: SpecialCodeCreate) -> SpecialCode:
        existing = special_code_repository.find_by_code(db, special_code_in.code)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe una excepción para este código")
        
        db_obj = SpecialCode(
            code=special_code_in.code,
            programming_code=special_code_in.programming_code
        )
        return special_code_repository.save(db, db_obj)

    @staticmethod
    def update(db: Session, special_code_id: str, special_code_in: SpecialCodeUpdate) -> SpecialCode:
        db_obj = special_code_repository.find_by_id(db, special_code_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Excepción no encontrada")
        
        update_data = special_code_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        return special_code_repository.save(db, db_obj)

    @staticmethod
    def delete(db: Session, special_code_id: str) -> None:
        db_obj = special_code_repository.find_by_id(db, special_code_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Excepción no encontrada")
        special_code_repository.delete(db, db_obj)
