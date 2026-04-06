import uuid
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
import pytz

class RecordStopwatchDetailSchema(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    quantity: float
    accumulated_duration: float
    creation_date: str
    code_code: str
    task_description: str
    task_type: Optional[str] = None
    task_activity: Optional[str] = None
    task_people: int
    comments: Optional[str] = None

    @field_validator('creation_date', mode='before')
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

class TaskStatusRequest(BaseModel):
    task_ids: List[uuid.UUID]

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    record_id: Optional[str] = None
    is_from_programming: bool
    real_start_time: Optional[str] = None
    real_end_time: Optional[str] = None

    @field_validator('real_start_time', 'real_end_time', mode='before')
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

class TimerStartPayload(BaseModel):
    start_time: Optional[datetime] = None
    is_from_programming: bool = False

class TimerStopPayload(BaseModel):
    quantity: float
    is_completed: Optional[bool] = None
    override_duration: Optional[float] = None

# Supervisor Schemas
class SupVerificationFields(BaseModel):
    area_limpia: Optional[bool] = None
    peso_verificado: Optional[bool] = None
    selladas: Optional[bool] = None
    contenedores_limpios: Optional[bool] = None
    informacion_correcta: Optional[bool] = None
    etiquetas_correctas: Optional[bool] = None
    contenedores_correctos: Optional[bool] = None
    verificacion_utensilios: Optional[bool] = None
    medidas_tomadas: Optional[str] = None

class SupStopwatch(SupVerificationFields):
    id: uuid.UUID
    task_id: uuid.UUID
    supervisor_id: uuid.UUID
    status: str
    accumulated_duration: float
    real_start_time: Optional[str] = None
    real_end_time: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

    @field_validator('real_start_time', 'real_end_time', 'created_at', 'updated_at', mode='before')
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True

class SupRecordStopwatch(SupVerificationFields):
    id: uuid.UUID
    task_id: uuid.UUID
    supervisor_id: uuid.UUID
    accumulated_duration: float
    comments: Optional[str] = None
    creation_date: str
    real_start_time: Optional[str] = None
    real_end_time: Optional[str] = None

    @field_validator('creation_date', 'real_start_time', 'real_end_time', mode='before')
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True

class SupTimerStopPayload(SupVerificationFields):
    comments: Optional[str] = None

class SupTaskStatusResponse(SupVerificationFields):
    task_id: str
    status: str
    accumulated_duration: float
    real_start_time: Optional[str] = None
    real_end_time: Optional[str] = None

    @field_validator('real_start_time', 'real_end_time', mode='before')
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v
