
from pydantic import BaseModel, ConfigDict, field_validator
import uuid
from datetime import datetime
import pytz
from app.modules.timing.models.state import TimerStatus

class StopwatchBase(BaseModel):
    task_id: uuid.UUID
    status: TimerStatus
    quantity: float
    accumulated_duration: float
    is_from_programming: bool = False
class StopwatchCreate(StopwatchBase):
    pass

class StopwatchUpdate(BaseModel):
    status: TimerStatus | None = None
    accumulated_duration: float | None = None
    is_from_programming: bool | None = None

class StopwatchInDBBase(StopwatchBase):
    id: uuid.UUID
    created_at: str
    update_at: str | None = None
    real_start_time: str | None = None
    real_end_time: str | None = None
    is_from_programming: bool

    @field_validator('created_at', 'update_at', 'real_start_time', 'real_end_time', mode='before')
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)

class Stopwatch(StopwatchInDBBase):
    pass
