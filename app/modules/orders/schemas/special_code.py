from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class SpecialCodeBase(BaseModel):
    code: str
    programming_code: Optional[str] = None

class SpecialCodeCreate(SpecialCodeBase):
    pass

class SpecialCodeUpdate(BaseModel):
    programming_code: Optional[str] = None

class SpecialCode(SpecialCodeBase):
    id: UUID

    class Config:
        from_attributes = True