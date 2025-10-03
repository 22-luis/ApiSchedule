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
    # Campos para reporte real
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
    real_quantity: Optional[int] = None
    comment: Optional[str] = None
    completed_by_user_id: Optional[UUID] = None

class TasksOrderRequest(BaseModel):
    tasks_order: List[ProgrammingTaskOrderIn]

class ProgrammingTaskOrderOut(BaseModel):
    task_id: UUID
    order: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    # Campos para reporte real
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
    real_quantity: Optional[int] = None
    comment: Optional[str] = None
    completed_by_user_id: Optional[UUID] = None

class ProgrammingReorderResponse(BaseModel):
    programming_id: UUID
    tasks: List[ProgrammingTaskOrderOut]

# Esquema para el reporte real del usuario
class ProgrammingTaskReportIn(BaseModel):
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
    real_quantity: Optional[int] = None
    comment: Optional[str] = None
    completed_by_user_id: Optional[UUID] = None

# Schema para programaciones disponibles por equipo
class AvailableProgrammingItem(BaseModel):
    id: str
    team_name: str
    date: str

class AvailableProgrammingResponse(BaseModel):
    team_id: str
    team_name: str
    available_programmings: List[AvailableProgrammingItem]
