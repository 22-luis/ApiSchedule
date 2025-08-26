"""
Rutas de la API para la gestión de programaciones: creación, actualización, reordenamiento de tareas, control de tiempo y reportes de ejecución.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.models.programming import Programming
from app.models.task import Task
from app.models.team import Team
from app.schemas.programming import ProgrammingCreate, ProgrammingRead, ProgrammingUpdate, ProgrammingTaskOrderIn, ProgrammingReorderResponse, ProgrammingTaskOrderOut, AvailableProgrammingResponse, AvailableProgrammingItem
from app.db.dependency import get_db
from app.utils.dependencies import get_current_user, require_roles
from datetime import date, datetime, timedelta, time
from uuid import UUID
from app.models.programming import ProgrammingTask
from app.schemas.task import TaskOut
from app.schemas.programming import ProgrammingTaskReportIn
from app.models.user import User
import sys
from pytz import timezone
from app.utils.order_status_service import OrderStatusService
from app.utils.programming_availability import update_programming_availability, update_all_programmings_availability_for_date
from app.models.programming import ProgrammingStatus

router = APIRouter(prefix="/programmings", tags=["programmings"])

# Helper para verificar si el usuario pertenece al equipo

def user_belongs_to_team(user, team_id):
    return any(str(team.id) == str(team_id) for team in getattr(user, "teams", []))

# Listar programaciones (admin/planner: todas, user: solo su equipo)
@router.get("/", response_model=List[ProgrammingRead])
def list_programmings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role.value in ("admin", "planner", "supervisor"):
        programmings = db.query(Programming).all()
    else:
        team_ids = [team.id for team in getattr(current_user, "teams", [])]
        programmings = db.query(Programming).filter(Programming.team_id.in_(team_ids)).all()
    # Serializar correctamente el campo 'tasks' como lista de UUIDs
    result = []
    for programming in programmings:
        result.append({
            "id": programming.id,
            "date": programming.date,
            "team_id": programming.team_id,
            "tasks": [t.id for t in programming.tasks]
        })
    return result

# Obtener programación por equipo y fecha (debe ir antes del endpoint por id)
@router.get("/by_team_date", response_model=dict)
def get_programming_by_team_date(team_id: str, date: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    print("[DEBUG] team_id:", team_id, type(team_id), "date:", date, type(date))
    try:
        # Convertir date a objeto date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        programming = db.query(Programming).filter_by(team_id=team_id, date=date_obj).first()
        if not programming:
            # Si no existe la programación, verificar si el usuario puede crearla
            print(f"[DEBUG] Programming not found - User role: {current_user.role.value}")
            print(f"[DEBUG] Programming not found - User teams: {[team.id for team in getattr(current_user, 'teams', [])]}")
            print(f"[DEBUG] Programming not found - Target team_id: {team_id}")
            print(f"[DEBUG] Programming not found - user_belongs_to_team result: {user_belongs_to_team(current_user, team_id)}")
            if current_user.role.value not in ("admin", "planner", "supervisor") and not user_belongs_to_team(current_user, team_id):
                raise HTTPException(status_code=403, detail="Not authorized")
            # Crear la programación automáticamente para usuarios autorizados
            programming = Programming(date=date_obj, team_id=team_id)
            db.add(programming)
            db.commit()
            db.refresh(programming)
        else:
            # Si existe la programación, verificar permisos de acceso
            print(f"[DEBUG] User role: {current_user.role.value}")
            print(f"[DEBUG] User teams: {[team.id for team in getattr(current_user, 'teams', [])]}")
            print(f"[DEBUG] Target team_id: {team_id}")
            print(f"[DEBUG] user_belongs_to_team result: {user_belongs_to_team(current_user, team_id)}")
            if current_user.role.value not in ("admin", "planner", "supervisor") and not user_belongs_to_team(current_user, team_id):
                raise HTTPException(status_code=403, detail="Not authorized")
        # Obtener tareas completas con datos de la tabla intermedia
        tasks = []
        # Usar joinedload para traer el objeto code completo y created_by_user
        task_ids = [pt.task_id for pt in programming.programming_tasks]
        tasks_with_code = db.query(Task).options(
            joinedload(Task.code),
            joinedload(Task.created_by_user)
        ).filter(Task.id.in_(task_ids)).all()
        task_map = {t.id: t for t in tasks_with_code}
        for pt in sorted(programming.programming_tasks, key=lambda pt: pt.order):
            task_obj = task_map.get(pt.task_id, pt.task)
            t = TaskOut.model_validate(task_obj, from_attributes=True).model_dump()
            t['start_time'] = pt.start_time
            t['end_time'] = pt.end_time
            t['order'] = pt.order
            t['real_start_time'] = getattr(pt, 'real_start_time', None)
            t['real_end_time'] = getattr(pt, 'real_end_time', None)
            t['real_quantity'] = getattr(pt, 'real_quantity', None)
            t['comment'] = getattr(pt, 'comment', None)
            t['is_completed'] = getattr(pt, 'is_completed', None)
            
            # Debug log para verificar datos de created_by_user
            if task_obj.created_by_user_id:
                print(f"[DEBUG] Task {task_obj.id}: created_by_user_id={task_obj.created_by_user_id}, created_by_user={task_obj.created_by_user}")
                print(f"[DEBUG] Task {task_obj.id}: created_by_user.name={getattr(task_obj.created_by_user, 'name', 'None') if task_obj.created_by_user else 'None'}")
            
            tasks.append(t)
        response = {
            "id": programming.id,
            "date": programming.date,
            "team_id": str(programming.team_id) if not isinstance(programming.team_id, UUID) else programming.team_id,
            "tasks": tasks
        }
        print("[DEBUG] response to return:", response)
        return response
    except Exception as e:
        print("[DEBUG] Exception in get_programming_by_team_date:", e)
        raise

# Obtener una programación
@router.get("/{programming_id}", response_model=ProgrammingRead)
def get_programming(programming_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if current_user.role.value not in ("admin", "planner", "supervisor") and not user_belongs_to_team(current_user, programming.team_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    }

# Crear programación (admin/planner/supervisor)
@router.post("/", response_model=ProgrammingRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["admin", "planner", "supervisor"]))])
def create_programming(data: ProgrammingCreate, db: Session = Depends(get_db)):
    # Verificar restricción única
    exists = db.query(Programming).filter_by(date=data.date, team_id=data.team_id).first()
    if exists:
        raise HTTPException(status_code=400, detail="Programming for this team and date already exists")
    programming = Programming(date=data.date, team_id=data.team_id)
    programming.tasks = db.query(Task).filter(Task.id.in_(data.task_ids)).all()
    db.add(programming)
    db.commit()
    db.refresh(programming)
    return programming

# Editar tareas de una programación (admin/planner/supervisor)
@router.put("/{programming_id}", response_model=ProgrammingRead, dependencies=[Depends(require_roles(["admin", "planner", "supervisor"]))])
def update_programming(programming_id: UUID, data: ProgrammingUpdate, db: Session = Depends(get_db)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if data.task_ids is not None:
        programming.tasks = db.query(Task).filter(Task.id.in_(data.task_ids)).all()
    db.commit()
    db.refresh(programming)
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    }

# Eliminar programación (admin/planner/supervisor)
@router.delete("/{programming_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["admin", "planner", "supervisor"]))])
def delete_programming(programming_id: UUID, db: Session = Depends(get_db)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    db.delete(programming)
    db.commit()
    return None

@router.post("/ensure_by_team_date", response_model=ProgrammingRead)
def ensure_programming_by_team_date(team_id: str = Query(...), date: date = Query(...), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    print("[DEBUG] current_user.role:", getattr(current_user, 'role', None))
    programming = db.query(Programming).filter_by(team_id=team_id, date=date).first()
    if programming:
        return programming
    # Solo admin/planner/supervisor pueden crear
    if current_user.role.value not in ("admin", "planner", "supervisor"):
        raise HTTPException(status_code=403, detail="Not authorized to create programming")
    programming = Programming(date=date, team_id=team_id)
    db.add(programming)
    db.commit()
    db.refresh(programming)
    return programming 

@router.post("/{programming_id}/add_task", response_model=ProgrammingRead)
def add_task_to_programming(
    programming_id: UUID,
    task_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if current_user.role.value not in ("admin", "planner", "supervisor"):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task not in programming.tasks:
        programming.tasks.append(task)
        db.commit()
        
        # Update programming availability after adding task
        update_programming_availability(db, programming)
        
        db.refresh(programming)
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    } 

@router.post("/{programming_id}/remove_task", response_model=ProgrammingRead)
def remove_task_from_programming(
    programming_id: UUID,
    task_id: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if current_user.role.value not in ("admin", "planner", "supervisor"):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task in programming.tasks:
        programming.tasks.remove(task)
        db.commit()
        
        # Update programming availability after removing task
        update_programming_availability(db, programming)
        
        db.refresh(programming)
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    } 

@router.put("/{programming_id}/reorder", response_model=ProgrammingReorderResponse)
async def reorder_programming_tasks(
    programming_id: UUID,
    request: Request,
    tasks_order: list[ProgrammingTaskOrderIn] = Body(...),
    base_time: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "planner", "supervisor"]))
):
    raw_body = await request.body()
    print("RAW PAYLOAD (antes de parsear):", raw_body)
    print("PARSED tasks_order:", tasks_order, file=sys.stderr)
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    programming_tasks_map = {pt.task_id: pt for pt in programming.programming_tasks}
    result = []
    current_time = None
    for item in sorted(tasks_order, key=lambda x: x.order):
        pt = programming_tasks_map.get(item.task_id)
        if not pt:
            raise HTTPException(status_code=404, detail=f"Task {item.task_id} not found in programming")
        pt.order = item.order
        if item.start_time and item.end_time:
            pt.start_time = item.start_time if isinstance(item.start_time, datetime) else datetime.fromisoformat(item.start_time)
            pt.end_time = item.end_time if isinstance(item.end_time, datetime) else datetime.fromisoformat(item.end_time)
            current_time = pt.end_time
        else:
            # Solo recalcula si NO se envían los valores
            if current_time is None:
                programming_date = programming.date
                weekday = programming_date.weekday()
                if base_time:
                    base_hour, base_minute = map(int, base_time.split(":"))
                    current_time = datetime.combine(programming_date, time(base_hour, base_minute))
                else:
                    if weekday == 5:
                        current_time = datetime.combine(programming_date, time(7, 30))
                    else:
                        current_time = datetime.combine(programming_date, time(7, 0))
            pt.start_time = current_time
            duration = getattr(pt.task, "minutes", 0) or 0
            pt.end_time = current_time + timedelta(minutes=duration)
            current_time = pt.end_time
        result.append(ProgrammingTaskOrderOut(
            task_id=pt.task_id,
            order=pt.order,
            start_time=pt.start_time,
            end_time=pt.end_time
        ))
    db.commit()
    
    # Update programming availability after reordering tasks
    update_programming_availability(db, programming)
    
    # Depuración: mostrar los valores actuales en la tabla intermedia
    refreshed_programming = db.query(Programming).get(programming_id)
    print('--- ProgrammingTask después de commit ---')
    if refreshed_programming:
        for pt in refreshed_programming.programming_tasks:
            print(f'Task {pt.task_id}: order={pt.order}, start_time={pt.start_time}, end_time={pt.end_time}')
    return ProgrammingReorderResponse(
        programming_id=programming_id,
        tasks=result
    ) 

@router.get("/{programming_id}/last_task", response_model=dict)
def get_last_task_of_programming(programming_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    # Buscar la ProgrammingTask con mayor end_time para esa programación
    last_prog_task = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.programming_id == programming_id)
        .order_by(ProgrammingTask.end_time.desc().nullslast())
        .first()
    )
    if not last_prog_task:
        raise HTTPException(status_code=404, detail="No tasks found for this programming")
    last_task = db.query(Task).filter(Task.id == last_prog_task.task_id).first()
    task_out = TaskOut.model_validate(last_task, from_attributes=True).model_dump()
    task_out['programming_end_time'] = last_prog_task.end_time.isoformat() if last_prog_task.end_time is not None else None
    return task_out 

@router.post("/{programming_id}/tasks/{task_id}/start_timer")
def start_task_timer(programming_id: str, task_id: str, data: dict = Body(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    # Solo el usuario asignado puede iniciar
    if pt.completed_by_user_id and pt.completed_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    sv_tz = timezone("America/El_Salvador")
    if data and data.get("real_start_time"):
        val = data["real_start_time"]
        if isinstance(val, str):
            pt.real_start_time = datetime.fromisoformat(val)
        else:
            pt.real_start_time = val
    else:
        pt.real_start_time = datetime.now(sv_tz)
    pt.completed_by_user_id = current_user.id
    
    # Actualizar estado de la orden usando el servicio centralizado
    OrderStatusService.update_order_status_for_task_start(db, pt)
    
    db.commit()
    return {"ok": True, "real_start_time": pt.real_start_time}

@router.post("/{programming_id}/tasks/{task_id}/stop_timer")
def stop_task_timer(programming_id: str, task_id: str, data: ProgrammingTaskReportIn = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    if pt.completed_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    sv_tz = timezone("America/El_Salvador")
    if hasattr(data, 'real_end_time') and data.real_end_time:
        val = data.real_end_time
        if isinstance(val, str):
            pt.real_end_time = datetime.fromisoformat(val)
        else:
            pt.real_end_time = val
    else:
        pt.real_end_time = datetime.now(sv_tz)
    pt.real_quantity = data.real_quantity
    db.commit()
    
    # Actualizar estado de la orden usando el servicio centralizado
    OrderStatusService.update_order_status_for_task_completion(db, pt)
    
    db.commit()
    return {"ok": True, "real_end_time": pt.real_end_time, "real_quantity": pt.real_quantity}

@router.post("/{programming_id}/tasks/{task_id}/comment")
def add_task_comment(programming_id: str, task_id: str, data: ProgrammingTaskReportIn = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    if pt.completed_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    pt.comment = data.comment
    db.commit()
    return {"ok": True, "comment": pt.comment} 

@router.post("/{programming_id}/tasks/{task_id}/toggle_status")
def toggle_task_status(programming_id: str, task_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    
    # Alternar el estado
    pt.is_completed = not bool(pt.is_completed)
    db.commit()
    
    # Actualizar estado de la orden usando el servicio centralizado
    OrderStatusService.update_order_status_for_task_completion(db, pt)
    
    db.refresh(pt)
    return {"is_completed": pt.is_completed}

@router.post("/{programming_id}/tasks/{task_id}/reprogram")
def reprogram_task(
    programming_id: str, 
    task_id: str, 
    new_date: date,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Reprograma una tarea para una nueva fecha y actualiza el estado de la orden correspondiente.
    """
    pt = db.query(ProgrammingTask).filter_by(programming_id=programming_id, task_id=task_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="ProgrammingTask not found")
    
    # Actualizar estado de la orden antes de reprogramar
    OrderStatusService.update_order_status_for_task_reprogramming(db, pt, new_date)
    
    # Aquí se podría agregar la lógica para mover la tarea a la nueva programación
    # Por ahora solo actualizamos el estado de la orden
    
    return {"message": "Task reprogrammed successfully"}


@router.post("/{programming_id}/check_availability")
def check_programming_availability(
    programming_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "planner", "supervisor"]))
):
    """
    Manually check and update programming availability based on the last task's end time.
    """
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    
    # Update programming availability
    status_changed = update_programming_availability(db, programming)
    
    return {
        "programming_id": programming_id,
        "current_status": programming.status.value,
        "status_changed": status_changed
    }


@router.post("/check_availability_by_date")
def check_programmings_availability_by_date(
    target_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "planner", "supervisor"]))
):
    """
    Check and update availability for all programmings on a specific date.
    """
    results = update_all_programmings_availability_for_date(db, target_date)
    
    return {
        "target_date": target_date.isoformat(),
        "results": results
    } 

@router.get("/team/{team_uuid}/available", response_model=AvailableProgrammingResponse)
def get_available_programmings_for_team(
    team_uuid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Obtiene las programaciones con estado 'available' para un equipo específico,
    desde la fecha actual hacia adelante. Si no existen programaciones futuras,
    crea una programación para el día siguiente a la última programación existente.
    
    Args:
        team_uuid: UUID del equipo
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Lista de programaciones disponibles con id, nombre del equipo y fecha
    """
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_uuid).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor") and not user_belongs_to_team(current_user, team_uuid):
        raise HTTPException(status_code=403, detail="Not authorized to access this team")
    
    # Obtener la fecha actual
    current_date = date.today()
    
    # Buscar programaciones disponibles desde la fecha actual
    available_programmings = (
        db.query(Programming)
        .filter(
            Programming.team_id == team_uuid,
            Programming.date >= current_date,
            Programming.status == ProgrammingStatus.available
        )
        .order_by(Programming.date)
        .all()
    )
    
    # Si no hay programaciones futuras disponibles, buscar la última programación del equipo
    if not available_programmings:
        last_programming = (
            db.query(Programming)
            .filter(Programming.team_id == team_uuid)
            .order_by(Programming.date.desc())
            .first()
        )
        
        # Si no hay ninguna programación, crear una para mañana
        if not last_programming:
            next_date = current_date + timedelta(days=1)
        else:
            # Crear una programación para el día siguiente a la última
            next_date = last_programming.date + timedelta(days=1)
        
        # Crear la nueva programación
        new_programming = Programming(
            date=next_date,
            team_id=team_uuid,
            status=ProgrammingStatus.available
        )
        db.add(new_programming)
        db.commit()
        db.refresh(new_programming)
        
        # Agregar la nueva programación a la lista
        available_programmings = [new_programming]
    
    # Preparar la respuesta usando el schema
    available_items = []
    for programming in available_programmings:
        available_items.append(AvailableProgrammingItem(
            id=str(programming.id),
            team_name=team.name,
            date=programming.date.isoformat()
        ))
    
    return AvailableProgrammingResponse(
        team_id=str(team_uuid),
        team_name=team.name,
        available_programmings=available_items
    )

@router.get("/team/{team_uuid}/available-only", response_model=AvailableProgrammingResponse)
def get_only_available_programmings_for_team(
    team_uuid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Obtiene SOLO las programaciones existentes con estado 'available' para un equipo específico,
    desde la fecha actual hacia adelante. NO crea nuevas programaciones automáticamente.
    
    Args:
        team_uuid: UUID del equipo
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Lista de programaciones disponibles existentes con id, nombre del equipo y fecha
    """
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_uuid).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor") and not user_belongs_to_team(current_user, team_uuid):
        raise HTTPException(status_code=403, detail="Not authorized to access this team")
    
    # Obtener la fecha actual
    current_date = date.today()
    
    # Buscar programaciones disponibles desde la fecha actual
    available_programmings = (
        db.query(Programming)
        .filter(
            Programming.team_id == team_uuid,
            Programming.date >= current_date,
            Programming.status == ProgrammingStatus.available
        )
        .order_by(Programming.date)
        .all()
    )
    
    # Preparar la respuesta usando el schema
    available_items = []
    for programming in available_programmings:
        available_items.append(AvailableProgrammingItem(
            id=str(programming.id),
            team_name=team.name,
            date=programming.date.isoformat()
        ))
    
    return AvailableProgrammingResponse(
        team_id=str(team_uuid),
        team_name=team.name,
        available_programmings=available_items
    )

@router.post("/team/{team_uuid}/create-next-available", response_model=AvailableProgrammingItem)
def create_next_available_programming_for_team(
    team_uuid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "planner", "supervisor"]))
):
    """
    Crea una nueva programación disponible para el día siguiente a la última programación existente del equipo.
    Solo para administradores, planners y supervisores.
    
    Args:
        team_uuid: UUID del equipo
        db: Sesión de base de datos
        current_user: Usuario autenticado (debe ser admin/planner/supervisor)
        
    Returns:
        La nueva programación creada
    """
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_uuid).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Buscar la última programación del equipo
    last_programming = (
        db.query(Programming)
        .filter(Programming.team_id == team_uuid)
        .order_by(Programming.date.desc())
        .first()
    )
    
    # Determinar la fecha para la nueva programación
    if not last_programming:
        next_date = date.today() + timedelta(days=1)
    else:
        next_date = last_programming.date + timedelta(days=1)
    
    # Verificar que no exista ya una programación para esa fecha
    existing_programming = (
        db.query(Programming)
        .filter(Programming.team_id == team_uuid, Programming.date == next_date)
        .first()
    )
    
    if existing_programming:
        raise HTTPException(
            status_code=400, 
            detail=f"Programming already exists for team {team.name} on date {next_date}"
        )
    
    # Crear la nueva programación
    new_programming = Programming(
        date=next_date,
        team_id=team_uuid,
        status=ProgrammingStatus.available
    )
    db.add(new_programming)
    db.commit()
    db.refresh(new_programming)
    
    return AvailableProgrammingItem(
        id=str(new_programming.id),
        team_name=team.name,
        date=new_programming.date.isoformat()
    )

@router.get("/{programming_id}/next-available-time", response_model=dict)
def get_next_available_time_for_programming(
    programming_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Obtiene el siguiente horario disponible para agregar una nueva tarea en una programación específica.
    
    Args:
        programming_id: UUID de la programación
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Diccionario con el siguiente horario disponible
    """
    from datetime import time
    
    # Verificar que la programación existe
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor") and not user_belongs_to_team(current_user, str(programming.team_id)):
        raise HTTPException(status_code=403, detail="Not authorized to access this programming")
    
    # Obtener las tareas de la programación ordenadas por end_time
    programming_tasks = (
        db.query(ProgrammingTask)
        .filter(ProgrammingTask.programming_id == programming_id)
        .order_by(ProgrammingTask.end_time.desc().nullslast())
        .all()
    )
    
    # Calcular el siguiente horario disponible
    if not programming_tasks:
        # Programación vacía - siguiente horario disponible es 7:00
        next_available_time = datetime.combine(programming.date, time(7, 0))
        message = "Programación vacía - siguiente horario disponible: 7:00"
    else:
        # Obtener la última tarea
        last_task = programming_tasks[0]  # Ya está ordenado por end_time desc
        
        if last_task.end_time:
            next_available_time = last_task.end_time
            message = f"Siguiente horario disponible después de la última tarea: {last_task.end_time.strftime('%H:%M')}"
        else:
            # Si la última tarea no tiene end_time, usar 7:00
            next_available_time = datetime.combine(programming.date, time(7, 0))
            message = "Última tarea sin horario - siguiente horario disponible: 7:00"
    
    # Obtener información del equipo
    team = db.query(Team).filter(Team.id == programming.team_id).first()
    team_name = team.name if team else "Equipo desconocido"
    
    return {
        "success": True,
        "message": message,
        "programming_id": str(programming_id),
        "team_id": str(programming.team_id),
        "team_name": team_name,
        "date": programming.date.isoformat(),
        "next_available_time": next_available_time.isoformat(),
        "next_available_time_formatted": next_available_time.strftime("%H:%M"),
        "total_tasks": len(programming_tasks),
        "is_empty": len(programming_tasks) == 0
    }

@router.get("/team/{team_id}/first-available-for-task", response_model=dict)
def get_first_available_programming_for_task(
    team_id: UUID,
    task_minutes: int = Query(..., description="Duración de la tarea en minutos"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Obtiene la primera programación disponible que pueda acomodar una tarea de duración específica.
    Implementa la lógica de "primer espacio disponible".
    
    Args:
        team_id: UUID del equipo
        task_minutes: Duración de la tarea en minutos
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Diccionario con la primera programación disponible que cumple las condiciones
    """
    from datetime import time
    
    # Verificar que el equipo existe
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verificar permisos del usuario
    if current_user.role.value not in ("admin", "planner", "supervisor") and not user_belongs_to_team(current_user, str(team_id)):
        raise HTTPException(status_code=403, detail="Not authorized to access this team")
    
    # Obtener todas las programaciones disponibles del equipo
    available_programmings = (
        db.query(Programming)
        .filter(
            Programming.team_id == team_id,
            Programming.status == ProgrammingStatus.available
        )
        .order_by(Programming.date)
        .all()
    )
    
    if not available_programmings:
        return {
            "success": False,
            "message": "No hay programaciones disponibles para este equipo",
            "selected_programming": None
        }
    
    # Configurar límites de tiempo
    time_limit = time(17, 40)  # 17:40
    tolerance_minutes = 5
    max_allowed_minutes = time_limit.hour * 60 + time_limit.minute + tolerance_minutes
    
    # Evaluar cada programación en orden para encontrar la primera que cumpla
    for programming in available_programmings:
        # Obtener las tareas de la programación
        programming_tasks = (
            db.query(ProgrammingTask)
            .filter(ProgrammingTask.programming_id == programming.id)
            .all()
        )
        
        # Calcular el tiempo actual de la programación
        current_end_minutes = 0
        
        if not programming_tasks:
            # Programación vacía - tiempo de inicio (7:00) + tarea de preparación (10 min)
            current_end_minutes = 7 * 60 + 10  # 7:10
        else:
            # Ordenar tareas por end_time y obtener la última
            sorted_tasks = sorted(programming_tasks, key=lambda x: x.end_time if x.end_time else time(0, 0))
            last_task = sorted_tasks[-1]
            
            if last_task.end_time:
                current_end_minutes = last_task.end_time.hour * 60 + last_task.end_time.minute
            else:
                current_end_minutes = 7 * 60  # 7:00
        
        # Calcular el tiempo final si se agrega la nueva tarea
        final_minutes = current_end_minutes + task_minutes
        
        # Verificar si esta programación cumple con el límite
        if final_minutes <= max_allowed_minutes:
            # ¡Encontramos la primera programación que cumple!
            current_end_time = time(current_end_minutes // 60, current_end_minutes % 60)
            final_time = time(final_minutes // 60, final_minutes % 60)
            
            return {
                "success": True,
                "message": f"Primera programación disponible encontrada que cumple con límite de tiempo",
                "selected_programming": {
                    "id": str(programming.id),
                    "date": programming.date.isoformat(),
                    "team_id": str(programming.team_id),
                    "team_name": team.name,
                    "current_end_time": current_end_time.isoformat(),
                    "task_minutes": task_minutes,
                    "final_time": final_time.isoformat(),
                    "time_limit": time_limit.isoformat(),
                    "tolerance_minutes": tolerance_minutes,
                    "total_existing_tasks": len(programming_tasks),
                    "is_empty": len(programming_tasks) == 0
                },
                "verification_details": {
                    "current_end_minutes": current_end_minutes,
                    "final_minutes": final_minutes,
                    "max_allowed_minutes": max_allowed_minutes,
                    "within_limit": True
                }
            }
    
    # Si ninguna programación cumple con el límite
    return {
        "success": False,
        "message": "Ninguna programación disponible cumple con el límite de tiempo",
        "selected_programming": None
    } 