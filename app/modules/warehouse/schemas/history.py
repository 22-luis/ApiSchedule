from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.modules.warehouse.models.history import WarehouseHistoryType

class WarehouseHistoryBase(BaseModel):
    lote: int
    code: str
    quantity: float
    type: WarehouseHistoryType
    user: str
    observations: Optional[str] = None

class WarehouseHistoryCreate(WarehouseHistoryBase):
    pass

class WarehouseHistoryOut(WarehouseHistoryBase):
    id: UUID
    timestamp: datetime

    class Config:
        from_attributes = True
