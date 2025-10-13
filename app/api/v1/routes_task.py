from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Dict, Any
from pydantic import BaseModel

from app.db.dependency import get_db
from app.models.task import Task
from app.models.team import Team
from app.models.user import User
from app.models.role import UserRole
from app.models.programming import Programming, ProgrammingTask
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.utils.dependencies import get_current_user, require_roles
from app.api.v1.replicate_pesado import replicate_task_to_pesado_if_needed
from app.utils.order_status_service import OrderStatusService
from app.utils.programming_availability import update_programming_availability_by_task

router = APIRouter(prefix="/tasks", tags=["tasks"])

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

    task_data = task.dict(exclude={"teamIds", "programming_id", "total_time"})
    return _create_task_logic(db, task_data, teams, programming, current_user)

class DuplicateTaskRequest(BaseModel):
    lote: str

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
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
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
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
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
    
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}

class DeleteTasksRequest(BaseModel):
    task_ids: List[str]

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
            db.delete(task)
        
        db.commit()
        
        return {"message": f"Successfully deleted {len(tasks_to_delete)} tasks."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during the deletion process: {e}"
        )

@router.get("/by-team/{team_id}", response_model=List[TaskOut])
def get_tasks_by_team(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Correctly filter for a many-to-many relationship
    tasks = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.teams.any(id=team_id)).all()
    
    return tasks