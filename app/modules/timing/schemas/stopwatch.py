
from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
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
    created_at: datetime
    update_at: datetime | None = None
    is_from_programming: bool

    model_config = ConfigDict(from_attributes=True)

class Stopwatch(StopwatchInDBBase):
    pass
