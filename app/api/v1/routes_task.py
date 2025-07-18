from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from typing import List
from app.models.task import Task
from app.models.team import Team
from app.schemas.task import TaskCreate, TaskUpdate, TaskOut
from app.models.user import User
from app.utils.dependencies import get_current_user, require_roles
from app.models.role import UserRole
from app.models.programming import Programming

# Opción 1: Router con prefijo específico
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskOut)
def create_task(
    task: TaskCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    # Verificar que los equipos existen
    teams = db.query(Team).filter(Team.id.in_(task.teamIds)).all()
    if len(teams) != len(task.teamIds):
        raise HTTPException(status_code=400, detail="One or more teams not found")
    # Verificar que la programación existe
    programming = db.query(Programming).filter(Programming.id == task.programming_id).first()
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    # Crear la tarea
    db_task = Task(
        minutes=task.minutes,
        start_time=task.start_time,
        end_time=task.end_time,
        teams=teams,
        # ...otros campos opcionales...
        code_id=task.code_id,
        lote=task.lote,
        quantity=task.quantity,
        specification=task.specification,
        preparation_id=task.preparation_id,
        people=task.people,
        performance=task.performance,
        material=task.material or "",
        presentation=task.presentation or "",
        fabricationCode=task.fabricationCode,
        usefulLife=task.usefulLife or "",
        related_task_code=task.related_task_code
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    # Asociar la tarea a la programación
    programming.tasks.append(db_task)
    db.commit()
    db.refresh(db_task)
    # Forzar string vacío en usefulLife y material/presentation en la respuesta
    response = db_task
    if response.usefulLife is None:
        response.usefulLife = ""
    if response.material is None:
        response.material = ""
    if response.presentation is None:
        response.presentation = ""
    return response

@router.get("/", response_model=List[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    tasks = db.query(Task).all()
    return tasks

@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    update_data = task_update.dict(exclude_unset=True)
    team_ids = update_data.pop("teamIds", None)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    if team_ids is not None:
        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        if len(teams) != len(team_ids):
            raise HTTPException(status_code=400, detail="One or more teams not found")
        db_task.teams = teams
    db.commit()
    db.refresh(db_task)
    return db_task

@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}

# Router adicional para rutas anidadas
nested_router = APIRouter()

@nested_router.get("/teams/{team_id}/tasks", response_model=List[TaskOut])
def get_tasks_by_team(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    tasks = db.query(Task).filter(Task.team_id == team_id).all()
    return tasks
