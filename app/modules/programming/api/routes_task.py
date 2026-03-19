from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import datetime
from app.modules.programming.repositories import task_repository
from app.shared.db.session import get_db
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.modules.programming.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.shared.utils.core.dependencies import get_current_user, require_roles
from app.shared.core.enums import TaskStatus
from app.modules.programming.services import task_service


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

    return task_service.create_task(db, task_data, team_ids, str(programming_id), current_user)

@router.post("/{task_id}/duplicate", response_model=TaskOut)
def duplicate_task(
    task_id: str,
    request: DuplicateTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    return task_service.duplicate_task(db, task_id, request.lote, current_user)

@router.get("/", response_model=List[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.USER))
):
    
    return task_repository.find_all(db) if hasattr(task_repository, 'find_all') else db.query(task_service.Task).all()

@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.USER))
):
    task = task_service.get_task_with_relations(db, task_id)
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
    return task_service.update_task(db, task_id, update_data, current_user)

@router.put("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: str,
    status_update: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return task_service.update_task_status(db, task_id, status_update.status, current_user)


@router.get("/{task_id}/real-time")
def get_task_real_time(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return task_service.get_task_real_time(db, task_id)


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    if task_service.delete_tasks(db, [task_id]):
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

    if task_service.delete_tasks(db, request.task_ids):
         return {"message": f"Successfully deleted {len(request.task_ids)} tasks."}
    
    raise HTTPException(status_code=404, detail="One or more tasks not found")
