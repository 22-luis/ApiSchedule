from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.available.models.availableModel import Available
from app.modules.available.schemas.available import AvailableCreate, AvailableUpdate

class AvailableRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, available_data: AvailableCreate) -> Available:
        db_item = Available(**available_data.dict())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def create_bulk(self, items: List[AvailableCreate]) -> List[Available]:
        objs = [Available(**item.dict()) for item in items]
        self.db.add_all(objs)
        self.db.commit()
        for o in objs:
            self.db.refresh(o)
        return objs

    def get_by_id(self, available_id) -> Optional[Available]:
        return self.db.query(Available).filter(Available.id == available_id).first()

    def get_list(self, skip: int = 0, limit: int = 100) -> List[Available]:
        return self.db.query(Available).offset(skip).limit(limit).all()

    def update(self, available_id, available_update: AvailableUpdate) -> Optional[Available]:
        db_item = self.get_by_id(available_id)
        if not db_item:
            return None
        update_data = available_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_item, field, value)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def delete(self, available_id) -> bool:
        db_item = self.get_by_id(available_id)
        if not db_item:
            return False
        self.db.delete(db_item)
        self.db.commit()
        return True

    def delete_all(self) -> int:
        deleted = self.db.query(Available).delete(synchronize_session=False)
        self.db.commit()
        return deleted
