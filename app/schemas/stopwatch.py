
from pydantic import BaseModel
import uuid
from datetime import datetime
from app.models.state import TimerStatus

class StopwatchBase(BaseModel):
    task_id: uuid.UUID
    status: TimerStatus
    quantity: float
    accumulated_duration: int

class StopwatchCreate(StopwatchBase):
    pass

class StopwatchUpdate(BaseModel):
    status: TimerStatus | None = None
    accumulated_duration: int | None = None

class StopwatchInDBBase(StopwatchBase):
    id: uuid.UUID
    created_at: datetime
    update_at: datetime | None = None

    class Config:
        orm_mode = True

class Stopwatch(StopwatchInDBBase):
    pass
