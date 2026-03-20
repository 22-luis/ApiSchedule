from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class SpecialCodeBase(BaseModel):
    code: str
    programming_code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True

class SpecialCodeCreate(SpecialCodeBase):
    pass

class SpecialCodeUpdate(BaseModel):
    programming_code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class SpecialCode(SpecialCodeBase):
    id: UUID

    class Config:
        from_attributes = True