from sqlalchemy import Session
from app.modules.available.models.availableModel import Available
from app.modules.available.schemas.available import AvailableCreate, AvailableUpdate, AvailableOut
import uuid
from typing import Optional,List
from datetime import date


class AvailableService:
     def __init__(self, db: Session):
        self.db = db

     def create(self,available_data:AvailableCreate)-> Available:

        db_compare = Available(**available_data.dict())
        self.db.add(db_compare)
        self.db.commit()
        self.db.refresh(db_compare)
        return db_compare