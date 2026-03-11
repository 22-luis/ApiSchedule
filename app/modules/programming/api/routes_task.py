from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel
import datetime

from app.shared.db.session import get_db
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.programming.models.task_status_log import TaskStatusLog
from app.modules.programming.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.shared.utils.core.dependencies import get_current_user, require_roles
from app.shared.core.enums import TaskStatus
from app.modules.programming.services.task_service import TaskService


router = APIRouter(prefix="/tasks", tags=["tasks"])

# --- Request Models ---

class TaskStatusUpdate(BaseModel):
    status: TaskStatus

class DuplicateTaskRequest(BaseModel):
    lote: str

class DeleteTasksRequest(BaseModel):
    task_ids: List[str]

# --- API Endpoints ---

@router.post("/", response_model=TaskOut)
def create_task(
    task: TaskCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    task_data = task.dict(exclude={"teamIds", "programming_id"})
    # Map total_time to minutes if minutes is not provided
    if "total_time" in task_data and not task_data.get("minutes"):
        task_data["minutes"] = task_data["total_time"]
    task_data.pop("total_time", None)

    team_ids = task.teamIds
    programming_id = task.programming_id

    return TaskService.create_task(db, task_data, team_ids, str(programming_id), current_user)

@router.post("/{task_id}/duplicate", response_model=TaskOut)
def duplicate_task(
    task_id: str,
    request: DuplicateTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    return TaskService.duplicate_task(db, task_id, request.lote, current_user)

@router.get("/", response_model=List[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.USER))
):
    # This remains simple enough for the route
    from app.modules.programming.models.task import Task
    tasks = db.query(Task).all()
    return tasks

@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.USER))
):
    task = TaskService.get_task_with_relations(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    update_data = task_update.dict(exclude_unset=True)
    return TaskService.update_task(db, task_id, update_data, current_user)

@router.put("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: str,
    status_update: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return TaskService.update_task_status(db, task_id, status_update.status, current_user)


@router.get("/{task_id}/real-time")
def get_task_real_time(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Log entries are business logic? Let's keep it here for now as it's a simple query
    # or move to TaskService if we want absolutely clean routes.
    from app.modules.programming.models.task import Task
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    log_entries = db.query(TaskStatusLog).filter(
        TaskStatusLog.task_id == task_id,
        TaskStatusLog.status == "in_progress" # TaskStatus.IN_PROGRESS.value might be better but checking original code
    ).all()

    total_time = datetime.timedelta(0)
    for entry in log_entries:
        if entry.end_time:
            total_time += entry.end_time - entry.start_time
        else:
            total_time += datetime.datetime.utcnow() - entry.start_time

    return {"task_id": task_id, "real_time_seconds": total_time.total_seconds()}


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    if TaskService.delete_tasks(db, [task_id]):
        return {"message": "Task deleted successfully"}
    raise HTTPException(status_code=404, detail="Task not found")

@router.post("/bulk-delete", status_code=200)
def delete_many_tasks(
    request: DeleteTasksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    if not request.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided.")

    if TaskService.delete_tasks(db, request.task_ids):
         return {"message": f"Successfully deleted {len(request.task_ids)} tasks."}
    
    raise HTTPException(status_code=404, detail="One or more tasks not found")
