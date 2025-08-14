import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator
from app.models.state import OrderStatus

class OrderCreate(BaseModel):
    lote: int
    code: str
    status: OrderStatus
    description: str
    quantity: int
    bin: int
    dueDate: datetime

    @field_validator('code', 'description')
    @classmethod
    def clean_string_fields(cls, v: str) -> str:
        """Limpia espacios en blanco al inicio y final de los campos string"""
        if isinstance(v, str):
            return v.strip()
        return v

class OrderOut(BaseModel):
    lote: int
    code: str
    status: OrderStatus
    description: str
    quantity: int
    bin: int
    dueDate: Optional[datetime] = None

    @field_validator('code', 'description')
    @classmethod
    def clean_string_fields(cls, v: str) -> str:
        """Limpia espacios en blanco al inicio y final de los campos string"""
        if isinstance(v, str):
            return v.strip()
        return v

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

# Esquema para respuesta paginada
class OrderPageOut(BaseModel):
    orders: list[OrderOut]
    total: int