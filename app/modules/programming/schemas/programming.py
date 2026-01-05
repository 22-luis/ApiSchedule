from typing import List, Optional
from datetime import date, datetime, time
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator

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

    model_config = ConfigDict(from_attributes=True)

# Schemas para el endpoint de reordenar tareas
class ProgrammingTaskOrderIn(BaseModel):
    task_id: UUID
    order: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    # Campos para reporte real
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
    real_quantity: Optional[float] = None
    duration_in_hours: Optional[float] = None
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
    real_quantity: Optional[float] = None
    duration_in_hours: Optional[float] = None
    comment: Optional[str] = None
    completed_by_user_id: Optional[UUID] = None

class ProgrammingReorderResponse(BaseModel):
    programming_id: UUID
    tasks: List[ProgrammingTaskOrderOut]


class ProgrammingTaskReportIn(BaseModel):
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
    real_quantity: Optional[float] = None
    comment: Optional[str] = None
    completed_by_user_id: Optional[UUID] = None

    @field_validator('real_quantity', mode='before')
    @classmethod
    def validate_real_quantity(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

class ToggleTaskStatusRequest(BaseModel):
    assigned_quantity: Optional[float] = None
    real_quantity: Optional[float] = None

    @field_validator('assigned_quantity', 'real_quantity', mode='before')
    @classmethod
    def validate_numeric_fields(cls, v):
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

# Schema para programaciones disponibles por equipo
class AvailableProgrammingItem(BaseModel):
    id: str
    team_name: str
    date: str

class AvailableProgrammingResponse(BaseModel):
    team_id: str
    team_name: str
    available_programmings: List[AvailableProgrammingItem]

# Schemas para el endpoint de resumen simplificado
class ProgrammingSummaryItem(BaseModel):
    lote: Optional[str] = None
    code: str
    description: Optional[str] = None
    quality_status: Optional[str] = None

class ProgrammingSummaryResponse(BaseModel):
    id: UUID
    date: date
    team_id: UUID
    tasks: List[ProgrammingSummaryItem]
