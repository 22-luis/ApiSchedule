import uuid
from datetime import datetime

from pydantic import BaseModel
from app.models.state import OrderState

class OrderCreate(BaseModel):
    lot: int
    code: str
    state: OrderState
    description: str
    amount: float
    bin: int
    created_at: datetime

class OrderOut(BaseModel):
    id: uuid.UUID
    lot: int
    code: str
    state: OrderState
    description: str
    amount: float
    bin: int
    created_at: datetime

    class Config:
        orm_mode = True