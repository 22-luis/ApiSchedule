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
