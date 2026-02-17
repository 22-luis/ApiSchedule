import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator
from app.modules.programming.models.state import OrderStatus

class OrderCreate(BaseModel):
    lote: int
    code: str
    status: Optional[OrderStatus] = OrderStatus.unprogrammed
    description: str
    quantity: float
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
    quantity: float
    bin: int
    dueDate: Optional[datetime] = None
    received_user: Optional[str] = None
    received_date: Optional[datetime] = None
    received_quantity: Optional[float] = None
    fabricated_quantity: Optional[float] = None
    missing_quantity: Optional[float] = None
    submitted_user: Optional[str] = None
    submitted_date: Optional[datetime] = None
    submitted_observations: Optional[str] = None
    is_hidden: Optional[bool] = False
    hidden_at: Optional[datetime] = None

    @field_validator('code', 'description')
    @classmethod
    def clean_string_fields(cls, v: str) -> str:
        """Limpia espacios en blanco al inicio y final de los campos string"""
        if isinstance(v, str):
            return v.strip()
        return v

    model_config = ConfigDict(from_attributes=True)

class OrderStatusUpdate(BaseModel):
    status: OrderStatus

class OrderDeliver(BaseModel):
    delivered_quantity: float
    submitted_observations: Optional[str] = None

# Esquema para respuesta paginada
class OrderPageOut(BaseModel):
    orders: list[OrderOut]
    total: int

class OrderWarehouseUpdate(BaseModel):
    received_user: Optional[str] = None
    received_date: Optional[datetime] = None
    received_quantity: Optional[float] = None
    missing_quantity: Optional[float] = None
    submitted_user: Optional[str] = None
    submitted_date: Optional[datetime] = None
    submitted_observations: Optional[str] = None
    is_hidden: Optional[bool] = None
    hidden_at: Optional[datetime] = None

class OrderWarehouseOut(BaseModel):
    lote: int
    code: str
    status: OrderStatus
    description: str
    quantity: float
    bin: int
    dueDate: datetime
    received_user: Optional[str] = None
    received_date: Optional[datetime] = None
    received_quantity: Optional[float] = None
    fabricated_quantity: Optional[float] = None
    missing_quantity: Optional[float] = None
    submitted_user: Optional[str] = None
    submitted_date: Optional[datetime] = None
    submitted_observations: Optional[str] = None
    is_hidden: Optional[bool] = False
    hidden_at: Optional[datetime] = None

