from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class OrderRuleBase(BaseModel):
    code: str
    programming_code: Optional[str] = None

class OrderRuleCreate(OrderRuleBase):
    pass

class OrderRuleUpdate(BaseModel):
    programming_code: Optional[str] = None

class OrderRule(OrderRuleBase):
    id: UUID

    class Config:
        from_attributes = True