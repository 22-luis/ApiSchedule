from typing import List, Optional
from datetime import date
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
    id: int
    tasks: List[UUID]

    class Config:
        from_attributes = True
