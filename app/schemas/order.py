import uuid
from datetime import datetime

from pydantic import BaseModel
from app.models.state import OrderStatus

class OrderCreate(BaseModel):
    lote: int
    code: str
    status: OrderStatus
    description: str
    quantity: int
    bin: int
    dueDate: datetime

class OrderOut(BaseModel):
    lote: int
    code: str
    status: OrderStatus
    description: str
    quantity: int
    bin: int
    dueDate: datetime

    class Config:
        from_attributes = True