from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProgrammingCreate(BaseModel):
    quantity: int
    minutes: int
    date: datetime
    task_id: str
    order_lote: int

class ProgrammingOut(BaseModel):
    id: str
    quantity: int
    minutes: int
    date: datetime
    task_id: str
    order_lote: int

    class Config:
        from_attributes = True
