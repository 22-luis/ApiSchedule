import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class RecordStopwatchDetailSchema(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    quantity: float
    accumulated_duration: float
    creation_date: datetime
    code_code: str
    task_description: str
    task_type: Optional[str] = None
    task_activity: Optional[str] = None
    task_people: int
    comments: Optional[str] = None

class TaskStatusRequest(BaseModel):
    task_ids: List[uuid.UUID]

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    record_id: Optional[str] = None
    is_from_programming: bool

class TimerStartPayload(BaseModel):
    start_time: Optional[datetime] = None
    is_from_programming: bool = False

class TimerStopPayload(BaseModel):
    quantity: float
    is_completed: Optional[bool] = None

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
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SupRecordStopwatch(SupVerificationFields):
    id: uuid.UUID
    task_id: uuid.UUID
    supervisor_id: uuid.UUID
    accumulated_duration: float
    comments: Optional[str] = None
    creation_date: datetime
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None

    class Config:
        from_attributes = True

class SupTimerStopPayload(SupVerificationFields):
    comments: Optional[str] = None

class SupTaskStatusResponse(SupVerificationFields):
    task_id: str
    status: str
    accumulated_duration: float
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
