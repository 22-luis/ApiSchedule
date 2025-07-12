import uuid
from pydantic import BaseModel
from typing import Optional
from app.schemas.team import TeamOut

class TaskCreate(BaseModel):
    code: str
    description: str
    unit: str
    type: str
    quantity: str
    minutes: int
    people: int
    performance: int
    material: str
    presentation: str
    fabricationCode: str
    usefulLife: str
    team_id: uuid.UUID  # ID del equipo obligatorio

class TaskUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    quantity: Optional[str] = None
    minutes: Optional[int] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None
    team_id: Optional[uuid.UUID] = None

class TaskOut(BaseModel):
    id: uuid.UUID
    code: str
    description: str
    unit: str
    type: str
    quantity: str
    minutes: int
    people: int
    performance: int
    material: str
    presentation: str
    fabricationCode: str
    usefulLife: str
    team_id: uuid.UUID
    team: TeamOut

    class Config:
        orm_mode = True
