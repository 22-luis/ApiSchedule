from pydantic import BaseModel, ConfigDict
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

    model_config = ConfigDict(from_attributes=True)

class RecordStopwatch(RecordStopwatchInDBBase):
    pass

class RecordStopwatchComment(BaseModel):
    comment: str