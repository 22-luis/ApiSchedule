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

router = APIRouter()

@router.post("/tasks", response_model=TaskOut)
def create_task(
    task: TaskCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == task.team_id).first()
    if not team:
        raise HTTPException(status_code=400, detail="Team not found")
    
    # Crear la tarea
    db_task = Task(
        code=task.code,
        description=task.description,
        unit=task.unit,
        type=task.type,
        quantity=task.quantity,
        minutes=task.minutes,
        people=task.people,
        performance=task.performance,
        material=task.material,
        presentation=task.presentation,
        fabricationCode=task.fabricationCode,
        usefulLife=task.usefulLife,
        team_id=task.team_id
    )
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.get("/tasks", response_model=List[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    tasks = db.query(Task).all()
    return tasks

@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Actualizar campos si se proporcionan
    update_data = task_update.dict(exclude_unset=True)
    team_id = update_data.pop("team_id", None)
    
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    # Actualizar equipo si se proporciona
    if team_id is not None:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=400, detail="Team not found")
        db_task.team_id = team_id
    
    db.commit()
    db.refresh(db_task)
    return db_task

@router.delete("/tasks/{task_id}")
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

@router.get("/teams/{team_id}/tasks", response_model=List[TaskOut])
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
