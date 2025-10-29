from pydantic import BaseModel
from datetime import datetime
import uuid

class RecordStopwatchBase(BaseModel):
    lote: str | None = None
    code: str
    description: str | None = None
    people: int | None = None
    quantity: float
    
class RecordStopwatchCreate(RecordStopwatchBase):
    pass

class RecordStopwatchUpdate(BaseModel):
    end_time: datetime
    real_quantity: float

class RecordStopwatchInDBBase(RecordStopwatchBase):
    id: uuid.UUID
    start_time: datetime
    end_time: datetime | None = None
    real_quantity: float | None = None

    class Config:
        orm_mode = True

class RecordStopwatch(RecordStopwatchInDBBase):
    pass
