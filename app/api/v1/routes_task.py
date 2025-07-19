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
from app.models.programming import ProgrammingTask
from sqlalchemy.orm import joinedload

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
        related_task_code=task.related_task_code,
        unit=task.unit,
        type=task.type,
        activity=task.activity,
        description=task.description
    )
    db.add(db_task)
    db.flush()  # Para asegurar que db_task.id esté disponible
    # Asociar la tarea a la programación seleccionada usando ProgrammingTask
    programming_task = ProgrammingTask(
        programming_id=programming.id,
        task_id=db_task.id,
        order=len(programming.programming_tasks) + 1,
        start_time=db_task.start_time,
        end_time=db_task.end_time
    )
    db.add(programming_task)
    db.commit()
    # Refresca la tarea con todas las relaciones
    full_task = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams)
    ).filter(Task.id == db_task.id).first()
    # Forzar string vacío en usefulLife y material/presentation en la respuesta
    if full_task.usefulLife is None:
        full_task.usefulLife = ""
    if full_task.material is None:
        full_task.material = ""
    if full_task.presentation is None:
        full_task.presentation = ""
    return full_task

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
    # Refresca la tarea con todas las relaciones
    full_task = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams)
    ).filter(Task.id == db_task.id).first()
    return full_task

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
