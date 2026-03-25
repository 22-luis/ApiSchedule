from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.orders.models.special_code import SpecialCode

def find_by_id(db: Session, special_code_id: str) -> Optional[SpecialCode]:
    return db.query(SpecialCode).filter(SpecialCode.id == special_code_id).first()

def find_by_code(db: Session, code: str) -> Optional[SpecialCode]:
    return db.query(SpecialCode).filter(SpecialCode.code == code).first()

def find_all(db: Session, skip: int = 0, limit: int = 100) -> List[SpecialCode]:
    return db.query(SpecialCode).offset(skip).limit(limit).all()

def save(db: Session, special_code: SpecialCode) -> SpecialCode:
    db.add(special_code)
    db.commit()
    db.refresh(special_code)
    return special_code

def delete(db: Session, special_code: SpecialCode) -> None:
    db.delete(special_code)
    db.commit()
