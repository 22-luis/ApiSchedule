import uuid
from pydantic import BaseModel
from typing import List, Optional
from app.schemas.team import TeamOut

class CodeCreate(BaseModel):
    code: str
    description: str
    unit: str
    type: str
    activity: str
    quantity: Optional[str] = None
    time: Optional[float] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: str
    presentation: str
    fabricationCode: Optional[str] = None
    usefulLife: str
    related_code_team: Optional[str] = None
    teamIds: Optional[List[uuid.UUID]] = None

    class Config:
        from_attributes = True

class CodeUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    activity: Optional[str] = None
    quantity: Optional[str] = None
    time: Optional[float] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None
    related_code_team: Optional[str] = None
    teamIds: Optional[List[uuid.UUID]] = None

class CodeOut(BaseModel):
    id: uuid.UUID
    code: str
    description: str
    unit: str
    type: str
    activity: str
    quantity: Optional[str] = None
    time: Optional[float] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: str
    presentation: str
    fabricationCode: Optional[str] = None
    usefulLife: str
    related_code_team: Optional[str] = None
    teams: List[TeamOut]

    class Config:
        from_attributes = True 