from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import uuid

class RecordStopwatchBase(BaseModel):
    lote: str | None = None
    code: str
    description: str | None = None
    people: int | None = None
    quantity: float
    
class RecordStopwatchCreate(RecordStopwatchBase):
    pass

class RecordStopwatchStart(BaseModel):
    start_time: Optional[datetime] = Field(None, description="Optional start time for the stopwatch")

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