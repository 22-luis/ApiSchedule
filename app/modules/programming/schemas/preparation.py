from pydantic import BaseModel, ConfigDict
from uuid import UUID

class PreparationCreate(BaseModel):
    description: str
    minutes: int

class PreparationOut(BaseModel):
    id: UUID
    description: str
    minutes: int

    model_config = ConfigDict(from_attributes=True)