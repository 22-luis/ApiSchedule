from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class OrderSurplusBase(BaseModel):
    lote: int
    date: date
    code: str
    description: Optional[str] = None
    original_quantity: float
    received_quantity: float
    surplus: float

class OrderSurplusCreate(OrderSurplusBase):
    pass

class OrderSurplusOut(OrderSurplusBase):
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
