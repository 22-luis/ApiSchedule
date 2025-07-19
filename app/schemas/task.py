import uuid
from pydantic import BaseModel
from typing import Optional, List
from app.schemas.team import TeamOut
from app.schemas.code import CodeOut
from app.schemas.preparation import PreparationOut
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    total_time: int
    minutes: Optional[int] = None
    start_time: datetime
    end_time: datetime
    teamIds: List[uuid.UUID]
    programming_id: uuid.UUID
    code_id: Optional[uuid.UUID] = None
    lote: Optional[str] = None
    quantity: Optional[int] = None
    specification: Optional[str] = None
    preparation_id: Optional[uuid.UUID] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None
    related_task_code: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    activity: Optional[str] = None
    description: Optional[str] = None

class TaskUpdate(BaseModel):
    code_id: Optional[uuid.UUID] = None
    preparation_id: Optional[uuid.UUID] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    lote: Optional[str] = None
    quantity: Optional[int] = None
    specification: Optional[str] = None
    minutes: Optional[int] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None
    related_task_code: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    activity: Optional[str] = None
    description: Optional[str] = None
    teamIds: Optional[List[uuid.UUID]] = None

class TaskOut(BaseModel):
    id: uuid.UUID
    code: Optional[CodeOut] = None
    lote: Optional[str] = None
    quantity: Optional[int] = None
    specification: Optional[str] = None
    preparation: Optional[PreparationOut] = None
    minutes: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    people: Optional[int] = None
    performance: Optional[int] = None
    material: str
    presentation: str
    fabricationCode: Optional[str] = None
    usefulLife: str
    teams: List[TeamOut]

    class Config:
        from_attributes = True
