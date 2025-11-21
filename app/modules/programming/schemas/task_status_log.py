from pydantic import BaseModel
from datetime import datetime
import uuid
from app.modules.programming.models.state import TaskStatus

class TaskStatusLogBase(BaseModel):
    status: TaskStatus
    start_time: datetime
    end_time: datetime | None = None

class TaskStatusLogCreate(BaseModel):
    status: TaskStatus

class TaskStatusLogOut(TaskStatusLogBase):
    id: uuid.UUID
    task_id: uuid.UUID

    class Config:
        orm_mode = True
