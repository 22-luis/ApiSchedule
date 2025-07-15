import uuid
from pydantic import BaseModel
from typing import Optional, List
from app.schemas.team import TeamOut

class TaskCreate(BaseModel):
    code: str
    description: str
    unit: str
    type: str
    activity: str
    quantity: str
    minutes: int
    people: int
    performance: int
    material: str
    presentation: str
    fabricationCode: str
    usefulLife: str
    teamIds: List[uuid.UUID]  # IDs de los equipos obligatorios

class TaskUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    activity: Optional[str] = None
    quantity: Optional[str] = None
    minutes: Optional[int] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None
    teamIds: Optional[List[uuid.UUID]] = None

class TaskOut(BaseModel):
    id: uuid.UUID
    code: str
    description: str
    unit: str
    type: str
    activity: str
    quantity: str
    minutes: int
    people: int
    performance: int
    material: str
    presentation: str
    fabricationCode: str
    usefulLife: str
    teams: List[TeamOut]

    class Config:
        from_attributes = True
