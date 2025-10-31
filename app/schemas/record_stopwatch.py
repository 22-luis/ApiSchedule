from pydantic import BaseModel
import uuid

class RecordStopwatchBase(BaseModel):
    task_id: uuid.UUID
    quantity: float
    accumulated_duration: float
class RecordStopwatchCreate(RecordStopwatchBase):
    pass

class RecordStopwatchUpdate(BaseModel):
    quantity: float | None = None
    accumulated_duration: int | None = None

class RecordStopwatchInDBBase(RecordStopwatchBase):
    id: uuid.UUID

    class Config:
        orm_mode = True

class RecordStopwatch(RecordStopwatchInDBBase):
    pass