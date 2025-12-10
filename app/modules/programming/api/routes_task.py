from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any
from pydantic import BaseModel
import datetime

from app.shared.db.session import get_db
from app.modules.programming.models.task import Task
from app.modules.core.models.team import Team, task_team_association
from app.modules.core.models.user import User
from app.modules.core.models.role import UserRole
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task_status_log import TaskStatusLog
from app.modules.programming.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.shared.utils.core.dependencies import get_current_user, require_roles
from app.modules.automation.services.replicate_pesado import replicate_task_to_pesado_if_needed
from app.shared.utils.business.order_status_service import OrderStatusService
from app.shared.utils.business.programming_availability import update_programming_availability_by_task, restore_programmings_availability
from app.shared.core.enums import TaskStatus, TaskType


router = APIRouter(prefix="/tasks", tags=["tasks"])

# --- Request Models ---

class TaskStatusUpdate(BaseModel):
    status: TaskStatus

class DuplicateTaskRequest(BaseModel):
    lote: str

class DeleteTasksRequest(BaseModel):
    task_ids: List[str]

# --- Helpers / Service Functions ---

def _get_task_with_relations(db: Session, task_id: str) -> Task:
    return db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.id == task_id).first()

def _check_user_team_permission(current_user: User, programming: Programming):
    if current_user.role == UserRole.USER:
        user_team_ids = {str(team.id) for team in current_user.teams}
        if str(programming.team_id) not in user_team_ids:
            raise HTTPException(status_code=403, detail="You can only create tasks for your assigned teams")

def _clean_task_response(task: Task) -> Task:
    if task:
        task.usefulLife = task.usefulLife or ""
        task.material = task.material or ""
        task.presentation = task.presentation or ""
    return task

def _create_task_logic(db: Session, task_data: Dict[str, Any], teams: List[Team], programming: Programming, current_user: User) -> Task:
    db_task = Task(
        **task_data,
        teams=teams,
        created_by_user_id=current_user.id
    )
    db.add(db_task)
    db.flush()  # Ensure db_task.id is available

    # Associate the task with the programming
    max_order = db.query(ProgrammingTask).filter(ProgrammingTask.programming_id == programming.id).count()
    programming_task = ProgrammingTask(
        programming_id=programming.id,
        task_id=db_task.id,
        order=max_order + 1,
        start_time=db_task.start_time,
        end_time=db_task.end_time
    )
    db.add(programming_task)

    # Trigger side effects (business logic)
    OrderStatusService.update_order_status_for_task_creation(db, db_task)

    db.commit()

    # Post-commit side effects
    if current_user.role in [UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR]:
        replicate_task_to_pesado_if_needed(db, db_task, programming.date)
        pass
    update_programming_availability_by_task(db, str(db_task.id))

    # Fetch the full task with relations for the response
    full_task = _get_task_with_relations(db, db_task.id)
    return _clean_task_response(full_task)

# --- API Endpoints ---

@router.post("/", response_model=TaskOut)
def create_task(
    task: TaskCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    # --- Validation and Authorization ---
    programming = db.query(Programming).filter(Programming.id == task.programming_id).first()
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")

    _check_user_team_permission(current_user, programming)

    teams = db.query(Team).filter(Team.id.in_(task.teamIds)).all()
    if len(teams) != len(task.teamIds):
        raise HTTPException(status_code=400, detail="One or more teams not found")

    task_data = task.dict(exclude={"teamIds", "programming_id"})
    # Map total_time to minutes if minutes is not provided
    if task.total_time and not task.minutes:
        task_data["minutes"] = task.total_time
    # Remove total_time from task_data as it's not a field in the Task model
    task_data.pop("total_time", None)
    return _create_task_logic(db, task_data, teams, programming, current_user)

@router.post("/{task_id}/duplicate", response_model=TaskOut)
def duplicate_task(
    task_id: str,
    request: DuplicateTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    # --- Validation and Authorization ---
    original_task = _get_task_with_relations(db, task_id)
    if not original_task:
        raise HTTPException(status_code=404, detail="Original task not found")

    programming = db.query(Programming).join(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).first()
    if not programming:
        raise HTTPException(status_code=404, detail="Task not associated with any programming")

    _check_user_team_permission(current_user, programming)

    # --- Core Logic ---
    task_data = {
        field: getattr(original_task, field) for field in Task.__table__.columns.keys()
        if field not in ['id', 'created_at', 'updated_at', 'created_by_user_id']
    }
    task_data['lote'] = request.lote # Set the new lote

    return _create_task_logic(db, task_data, original_task.teams, programming, current_user)

@router.get("/", response_model=List[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.USER))
):
    tasks = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).all()
    return tasks

@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.TIMEKEEPER, UserRole.USER))
):
    task = _get_task_with_relations(db, task_id)
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
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    update_data = task_update.dict(exclude_unset=True)
    team_ids = update_data.pop("teamIds", None)
    
    updating_times = 'start_time' in update_data or 'end_time' in update_data
    
    for field, value in update_data.items():
        setattr(db_task, field, value)
    if team_ids is not None:
        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        if len(teams) != len(team_ids):
            raise HTTPException(status_code=400, detail="One or more teams not found")
        db_task.teams = teams
    
    if updating_times:
        programming_tasks = db.query(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).all()
        for pt in programming_tasks:
            if 'start_time' in update_data:
                pt.start_time = update_data['start_time']
            if 'end_time' in update_data:
                pt.end_time = update_data['end_time']
    
    db.commit()
    
    if updating_times:
        update_programming_availability_by_task(db, task_id)
    
    full_task = _get_task_with_relations(db, task_id)
    return full_task

@router.put("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: str,
    status_update: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_task = _get_task_with_relations(db, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if db_task.is_completed:
        raise HTTPException(status_code=400, detail="Cannot change status of a completed task")

    new_status = status_update.status
    current_status = db_task.status

    if new_status == current_status:
        return _clean_task_response(db_task)

    # Role-based authorization for pausing
    if new_status == TaskStatus.PAUSED and current_user.role == UserRole.USER:
        allowed_task_types = [TaskType.M1, TaskType.M12, TaskType.M13, TaskType.M15]
        if db_task.type not in allowed_task_types:
            raise HTTPException(status_code=403, detail="You are not authorized to pause this type of task")

    now = datetime.datetime.utcnow()

    # Find the current status log entry and end it
    current_log_entry = db.query(TaskStatusLog).filter(
        TaskStatusLog.task_id == db_task.id,
        TaskStatusLog.end_time == None
    ).first()

    if current_log_entry:
        current_log_entry.end_time = now

    # Create a new status log entry
    new_log_entry = TaskStatusLog(
        task_id=db_task.id,
        status=new_status.value,
        start_time=now
    )
    db.add(new_log_entry)

    # Update the task's status
    db_task.status = new_status.value

    db.commit()
    db.refresh(db_task)

    return _clean_task_response(db_task)


@router.get("/{task_id}/real-time")
def get_task_real_time(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    log_entries = db.query(TaskStatusLog).filter(
        TaskStatusLog.task_id == task_id,
        TaskStatusLog.status == TaskStatus.IN_PROGRESS.value
    ).all()

    total_time = datetime.timedelta(0)
    for entry in log_entries:
        if entry.end_time:
            total_time += entry.end_time - entry.start_time
        else:
            # If the task is currently in progress, calculate the time until now
            total_time += datetime.datetime.utcnow() - entry.start_time

    return {"task_id": task_id, "real_time_seconds": total_time.total_seconds()}


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    OrderStatusService.update_order_status_for_task_deletion(db, db_task)
    update_programming_availability_by_task(db, task_id)
    
    # Manually delete associations to handle potential duplicates
    db.execute(
        task_team_association.delete().where(task_team_association.c.task_id == task_id)
    )
    
    db.delete(db_task)
    db.commit()
    
    # Restaurar disponibilidad de programaciones (por si se liberó espacio)
    restore_programmings_availability(db)
    
    return {"message": "Task deleted successfully"}

@router.post("/bulk-delete", status_code=200)
def delete_many_tasks(
    request: DeleteTasksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Deletes multiple tasks by their IDs. This is an all-or-nothing operation.
    If any task fails to delete, the entire transaction is rolled back.
    """
    if not request.task_ids:
        raise HTTPException(status_code=400, detail="No task IDs provided.")

    tasks_to_delete = db.query(Task).filter(Task.id.in_(request.task_ids)).all()

    if len(tasks_to_delete) != len(set(request.task_ids)):
        found_ids = {str(t.id) for t in tasks_to_delete}
        missing_ids = set(request.task_ids) - found_ids
        raise HTTPException(
            status_code=404,
            detail=f"Tasks with following IDs not found: {', '.join(missing_ids)}"
        )

    try:
        for task in tasks_to_delete:
            OrderStatusService.update_order_status_for_task_deletion(db, task)
            update_programming_availability_by_task(db, str(task.id))
            
            # Manually delete associations to handle potential duplicates
            db.execute(
                task_team_association.delete().where(task_team_association.c.task_id == task.id)
            )
            
            db.delete(task)
        
        db.commit()
        
        # Restaurar disponibilidad de programaciones (por si se liberó espacio)
        restore_programmings_availability(db)
        
        return {"message": f"Successfully deleted {len(tasks_to_delete)} tasks."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during the deletion process: {e}"
        )
