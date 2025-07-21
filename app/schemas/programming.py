from typing import List, Optional
from datetime import date, datetime, time
from uuid import UUID
from pydantic import BaseModel

class ProgrammingBase(BaseModel):
    date: date
    team_id: UUID

class ProgrammingCreate(ProgrammingBase):
    task_ids: List[int]

class ProgrammingUpdate(BaseModel):
    task_ids: Optional[List[int]] = None

class ProgrammingRead(ProgrammingBase):
    id: UUID
    tasks: List[UUID]

    class Config:
        from_attributes = True

# Schemas para el endpoint de reordenar tareas
class ProgrammingTaskOrderIn(BaseModel):
    task_id: UUID
    order: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class ProgrammingTaskOrderOut(BaseModel):
    task_id: UUID
    order: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class ProgrammingReorderResponse(BaseModel):
    programming_id: UUID
    tasks: List[ProgrammingTaskOrderOut]
