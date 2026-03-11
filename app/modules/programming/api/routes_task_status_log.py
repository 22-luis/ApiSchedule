from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.modules.programming.schemas.task_status_log import TaskStatusLogCreate, TaskStatusLogOut
from app.modules.programming.services.task_service import TaskService
import uuid
from typing import List

router = APIRouter()

@router.post("/tasks/{task_id}/status", response_model=TaskStatusLogOut)
def change_task_status(
    task_id: uuid.UUID,
    status_in: TaskStatusLogCreate,
    db: Session = Depends(get_db)
):
    """
    Change the status of a task and log the change.
    - **task_id**: The ID of the task to update.
    - **status_in**: The new status for the task.
    """
    return TaskService.change_task_status(db, str(task_id), status_in.status.value)

@router.get("/tasks/{task_id}/status-logs", response_model=List[TaskStatusLogOut])
def get_task_status_logs(
    task_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get all status logs for a specific task.
    - **task_id**: The ID of the task.
    """
    return TaskService.get_status_logs(db, str(task_id))
