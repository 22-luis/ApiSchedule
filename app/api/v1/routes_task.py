"""
Rutas de la API para la gestión de tareas: creación, consulta, actualización y eliminación, así como operaciones relacionadas con equipos y programaciones.
"""
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
from app.api.v1.replicate_pesado import replicate_task_to_pesado_if_needed
from sqlalchemy.orm import joinedload
from pydantic import BaseModel
from app.utils.order_status_service import OrderStatusService
from app.utils.programming_availability import update_programming_availability_by_task

# Opción 1: Router con prefijo específico
router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=TaskOut)
def create_task(
    task: TaskCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    # Verificar que los equipos existen
    teams = db.query(Team).filter(Team.id.in_(task.teamIds)).all()
    if len(teams) != len(task.teamIds):
        raise HTTPException(status_code=400, detail="One or more teams not found")
    
    # Verificar que la programación existe
    programming = db.query(Programming).filter(Programming.id == task.programming_id).first()
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    
    # Si el usuario es USER, verificar que pertenece al equipo de la programación
    if current_user.role == UserRole.USER:
        user_team_ids = [str(team.id) for team in current_user.teams]
        programming_team_id = str(programming.team_id)
        if programming_team_id not in user_team_ids:
            raise HTTPException(status_code=403, detail="You can only create tasks for your assigned teams")
    
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
        description=task.description,
        created_by_user_id=current_user.id
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

    # Actualizar estado de la orden usando el servicio centralizado
    OrderStatusService.update_order_status_for_task_creation(db, db_task)
    
    # Verificar si la programación es para hoy y actualizar estado automáticamente
    OrderStatusService.update_order_status_for_programming_date(db, programming_task)

    db.commit()
    # Refresca la tarea con todas las relaciones
    full_task = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.id == db_task.id).first()
    # Forzar string vacío en usefulLife y material/presentation en la respuesta
    if full_task.usefulLife is None:
        full_task.usefulLife = ""
    if full_task.material is None:
        full_task.material = ""
    if full_task.presentation is None:
        full_task.presentation = ""
    # Lógica automática para replicar en equipo pesado si aplica
    replicate_task_to_pesado_if_needed(db, db_task, programming.date)
    
    # Update programming availability based on the new task
    update_programming_availability_by_task(db, str(db_task.id))
    
    return full_task

class DuplicateTaskRequest(BaseModel):
    lote: str

@router.post("/{task_id}/duplicate", response_model=TaskOut)
def duplicate_task(
    task_id: str,
    request: DuplicateTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """Duplicate an existing task with a new lote"""
    # Get the original task
    original_task = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.id == task_id).first()
    
    if not original_task:
        raise HTTPException(status_code=404, detail="Original task not found")
    
    # Get the programming through the ProgrammingTask association
    programming_task_assoc = db.query(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).first()
    if not programming_task_assoc:
        raise HTTPException(status_code=404, detail="Task not found in any programming")
    
    programming = db.query(Programming).filter(Programming.id == programming_task_assoc.programming_id).first()
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    
    # If the user is USER, verify that they belong to the programming team
    if current_user.role == UserRole.USER:
        user_team_ids = [str(team.id) for team in current_user.teams]
        programming_team_id = str(programming.team_id)
        if programming_team_id not in user_team_ids:
            raise HTTPException(status_code=403, detail="You can only duplicate tasks for your assigned teams")
    
    # Create the duplicated task
    duplicated_task = Task(
        minutes=original_task.minutes,
        start_time=original_task.start_time,
        end_time=original_task.end_time,
        teams=original_task.teams,
        code_id=original_task.code_id,
        lote=request.lote,  # Use the new lote from request
        quantity=original_task.quantity,
        specification=original_task.specification,
        preparation_id=original_task.preparation_id,
        people=original_task.people,
        performance=original_task.performance,
        material=original_task.material or "",
        presentation=original_task.presentation or "",
        fabricationCode=original_task.fabricationCode,
        usefulLife=original_task.usefulLife or "",
        related_task_code=original_task.related_task_code,
        unit=original_task.unit,
        type=original_task.type,
        activity=original_task.activity,
        description=original_task.description,
        created_by_user_id=current_user.id
    )
    db.add(duplicated_task)
    db.flush()  # To ensure duplicated_task.id is available
    
    # Associate the task to the programming using ProgrammingTask
    # Get the next order number
    max_order = db.query(ProgrammingTask).filter(ProgrammingTask.programming_id == programming.id).count()
    programming_task = ProgrammingTask(
        programming_id=programming.id,
        task_id=duplicated_task.id,
        order=max_order + 1,
        start_time=duplicated_task.start_time,
        end_time=duplicated_task.end_time
    )
    db.add(programming_task)
    
    # Actualizar estado de la orden usando el servicio centralizado
    OrderStatusService.update_order_status_for_task_creation(db, duplicated_task)
    
    # Verificar si la programación es para hoy y actualizar estado automáticamente
    OrderStatusService.update_order_status_for_programming_date(db, programming_task)
    
    db.commit()
    
    # Refresh the task with all relationships
    full_task = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.id == duplicated_task.id).first()
    
    # Force empty string in usefulLife and material/presentation in the response
    if full_task.usefulLife is None:
        full_task.usefulLife = ""
    if full_task.material is None:
        full_task.material = ""
    if full_task.presentation is None:
        full_task.presentation = ""
    
    # Automatic logic to replicate in heavy team if applicable
    replicate_task_to_pesado_if_needed(db, full_task, programming.date)
    
    # Update programming availability based on the new task
    update_programming_availability_by_task(db, str(duplicated_task.id))
    
    return full_task

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
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    task = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    update_data = task_update.dict(exclude_unset=True)
    team_ids = update_data.pop("teamIds", None)
    
    # Verificar si se están actualizando los tiempos
    updating_times = 'start_time' in update_data or 'end_time' in update_data
    
    for field, value in update_data.items():
        setattr(db_task, field, value)
    if team_ids is not None:
        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        if len(teams) != len(team_ids):
            raise HTTPException(status_code=400, detail="One or more teams not found")
        db_task.teams = teams
    
    # Si se están actualizando los tiempos, también actualizar ProgrammingTask
    if updating_times:
        programming_tasks = db.query(ProgrammingTask).filter(ProgrammingTask.task_id == task_id).all()
        for pt in programming_tasks:
            if 'start_time' in update_data:
                pt.start_time = update_data['start_time']
            if 'end_time' in update_data:
                pt.end_time = update_data['end_time']
    
    db.commit()
    
    # Update programming availability if times were changed
    if updating_times:
        update_programming_availability_by_task(db, task_id)
    
    # Refresca la tarea con todas las relaciones
    full_task = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.id == db_task.id).first()
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
    
    # Actualizar estado de la orden antes de eliminar la tarea
    OrderStatusService.update_order_status_for_task_deletion(db, db_task)
    
    # Update programming availability before deleting the task
    update_programming_availability_by_task(db, task_id)
    
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
    
    tasks = db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.team_id == team_id).all()
    return tasks