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
    quantity: Optional[str] = None
    minutes: Optional[int] = None
    people: int
    performance: Optional[int] = None
    material: str
    presentation: str
    fabricationCode: Optional[str] = None
    usefulLife: str
    teamIds: List[uuid.UUID]  # IDs de los equipos obligatorios
    parentId: Optional[uuid.UUID] = None

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
    parentId: Optional[uuid.UUID] = None

class TaskOut(BaseModel):
    id: uuid.UUID
    code: str
    description: str
    unit: str
    type: str
    activity: str
    quantity: Optional[str] = None
    minutes: Optional[int] = None
    people: int
    performance: Optional[int] = None
    material: str
    presentation: str
    fabricationCode: Optional[str] = None
    usefulLife: str
    teams: List[TeamOut]
    parentId: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True
