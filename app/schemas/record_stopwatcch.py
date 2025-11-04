from datetime import datetime
from pydantic import BaseModel

class RecordStopwatchBase(BaseModel):
    code: str
    description: str | None = None
    people: int | None = None
    quantity: float
    real_quantity: float
    start_time: str
    end_time: str | None = None