from pydantic import BaseModel, ConfigDict, field_validator
import uuid
from datetime import datetime
import pytz

class RecordStopwatchBase(BaseModel):
    task_id: uuid.UUID
    quantity: float
    accumulated_duration: float
    comments: str | None = None
class RecordStopwatchCreate(RecordStopwatchBase):
    pass

class RecordStopwatchUpdate(BaseModel):
    quantity: float | None = None
    accumulated_duration: int | None = None

class RecordStopwatchInDBBase(RecordStopwatchBase):
    id: uuid.UUID
    creation_date: str
    real_start_time: str | None = None
    real_end_time: str | None = None

    @field_validator('creation_date', 'real_start_time', 'real_end_time', mode='before')
    @classmethod
    def format_datetime(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    model_config = ConfigDict(from_attributes=True)

class RecordStopwatch(RecordStopwatchInDBBase):
    pass

class RecordStopwatchComment(BaseModel):
    comment: str
