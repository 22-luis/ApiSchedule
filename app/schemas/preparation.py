from pydantic import BaseModel
from uuid import UUID

class PreparationCreate(BaseModel):
    description: str
    minutes: int

class PreparationOut(BaseModel):
    id: UUID
    description: str
    minutes: int

    class Config:
        from_attributes = True