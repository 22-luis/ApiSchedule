from pydantic import BaseModel, ConfigDict, field_validator
import uuid
from datetime import datetime

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
    creation_date: datetime
    real_start_time: datetime | None = None
    real_end_time: datetime | None = None

    @field_validator('creation_date', 'real_start_time', 'real_end_time', mode='before')
    @classmethod
    def strip_tzinfo(cls, v):
        if isinstance(v, datetime):
            return v.replace(tzinfo=None)
        return v

    model_config = ConfigDict(from_attributes=True)

class RecordStopwatch(RecordStopwatchInDBBase):
    pass

class RecordStopwatchComment(BaseModel):
    comment: str
