from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.models.task import Task
from app.models.task_status_log import TaskStatusLog
from app.schemas.task_status_log import TaskStatusLogCreate, TaskStatusLogOut
from app.models.state import TaskStatus
import datetime
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
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Find the latest status log for the task
    latest_log = db.query(TaskStatusLog).filter(TaskStatusLog.task_id == task_id).order_by(TaskStatusLog.start_time.desc()).first()

    if latest_log:
        # If the new status is the same as the current one, do nothing
        if latest_log.status == status_in.status:
            return latest_log
        
        # Update the end_time of the last log
        latest_log.end_time = datetime.datetime.utcnow()
        db.add(latest_log)

    # Create a new status log
    new_log = TaskStatusLog(
        task_id=task_id,
        status=status_in.status,
        start_time=datetime.datetime.utcnow()
    )
    db.add(new_log)

    # Update the task's current status
    task.status = status_in.status.value
    db.add(task)

    db.commit()
    db.refresh(new_log)
    return new_log

@router.get("/tasks/{task_id}/status-logs", response_model=List[TaskStatusLogOut])
def get_task_status_logs(
    task_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get all status logs for a specific task.
    - **task_id**: The ID of the task.
    """
    logs = db.query(TaskStatusLog).filter(TaskStatusLog.task_id == task_id).order_by(TaskStatusLog.start_time.asc()).all()
    return logs
