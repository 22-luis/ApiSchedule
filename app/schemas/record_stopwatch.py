from pydantic import BaseModel
import uuid
<<<<<<< HEAD
from datetime import datetime
=======
>>>>>>> 6e0846ff0532e9c61dd2cbf57cd1b22aab21b7be

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
<<<<<<< HEAD
    creation_date: datetime
=======
>>>>>>> 6e0846ff0532e9c61dd2cbf57cd1b22aab21b7be

    class Config:
        orm_mode = True

class RecordStopwatch(RecordStopwatchInDBBase):
    pass