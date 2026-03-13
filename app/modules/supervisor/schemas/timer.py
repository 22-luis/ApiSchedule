import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.modules.timer.models.state import TimerStatus

class SupVerificationFields(BaseModel):
    area_limpia: bool = False
    peso_verificado: bool = False
    selladas: bool = False
    contenedores_limpios: bool = False
    informacion_correcta: bool = False
    etiquetas_correctas: bool = False
    contenedores_correctos: bool = False
    medidas_tomadas: Optional[str] = None

class SupStopwatchBase(BaseModel):
    task_id: uuid.UUID
    status: TimerStatus
    accumulated_duration: float
    real_start_time: Optional[datetime] = None

class SupStopwatchCreate(SupStopwatchBase, SupVerificationFields):
    supervisor_id: uuid.UUID

class SupStopwatch(SupStopwatchBase, SupVerificationFields):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supervisor_id: uuid.UUID
    real_end_time: Optional[datetime] = None
    created_at: Optional[datetime] = None

class SupRecordStopwatchBase(BaseModel):
    task_id: uuid.UUID
    accumulated_duration: float
    comments: Optional[str] = None

class SupRecordStopwatch(SupRecordStopwatchBase, SupVerificationFields):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    supervisor_id: uuid.UUID
    creation_date: datetime
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None

class SupTimerStopPayload(SupVerificationFields):
    comments: Optional[str] = None

class SupTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    accumulated_duration: float
    real_start_time: Optional[datetime] = None
    real_end_time: Optional[datetime] = None
    # Include verification fields in status response as well
    area_limpia: bool = False
    peso_verificado: bool = False
    selladas: bool = False
    contenedores_limpios: bool = False
    informacion_correcta: bool = False
    etiquetas_correctas: bool = False
    contenedores_correctos: bool = False
    medidas_tomadas: Optional[str] = None
    comments: Optional[str] = None
