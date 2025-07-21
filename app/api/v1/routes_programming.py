from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.programming import Programming
from app.models.task import Task
from app.models.team import Team
from app.schemas.programming import ProgrammingCreate, ProgrammingRead, ProgrammingUpdate, ProgrammingTaskOrderIn, ProgrammingReorderResponse, ProgrammingTaskOrderOut
from app.db.dependency import get_db
from app.utils.dependencies import get_current_user, require_roles
from datetime import date, datetime, timedelta, time
from uuid import UUID
from app.models.programming import ProgrammingTask
from app.schemas.task import TaskOut
import sys

router = APIRouter(prefix="/programmings", tags=["programmings"])

# Helper para verificar si el usuario pertenece al equipo

def user_belongs_to_team(user, team_id):
    return any(team.id == team_id for team in getattr(user, "teams", []))

# Listar programaciones (admin/planner: todas, user: solo su equipo)
@router.get("/", response_model=List[ProgrammingRead])
def list_programmings(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role.value in ("admin", "planner", "supervisor"):
        return db.query(Programming).all()
    # Usuario común: solo las de sus equipos
    team_ids = [team.id for team in getattr(current_user, "teams", [])]
    return db.query(Programming).filter(Programming.team_id.in_(team_ids)).all()

# Obtener programación por equipo y fecha (debe ir antes del endpoint por id)
@router.get("/by_team_date", response_model=dict)
def get_programming_by_team_date(team_id: str, date: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    print("[DEBUG] team_id:", team_id, type(team_id), "date:", date, type(date))
    try:
        # Convertir date a objeto date
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        programming = db.query(Programming).filter_by(team_id=team_id, date=date_obj).first()
        if not programming:
            raise HTTPException(status_code=404, detail="Programming not found")
        if current_user.role.value not in ("admin", "planner") and not user_belongs_to_team(current_user, team_id):
            raise HTTPException(status_code=403, detail="Not authorized")
        # Obtener tareas completas con datos de la tabla intermedia
        tasks = []
        for pt in sorted(programming.programming_tasks, key=lambda pt: pt.order):
            t = TaskOut.model_validate(pt.task, from_attributes=True).model_dump()
            t['start_time'] = pt.start_time
            t['end_time'] = pt.end_time
            t['order'] = pt.order
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
    if current_user.role not in ("admin", "planner") and not user_belongs_to_team(current_user, programming.team_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return {
        "id": programming.id,
        "date": programming.date,
        "team_id": programming.team_id,
        "tasks": [t.id for t in programming.tasks]
    }

# Crear programación (solo admin/planner)
@router.post("/", response_model=ProgrammingRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(["admin", "planner"]))])
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

# Editar tareas de una programación (solo admin/planner)
@router.put("/{programming_id}", response_model=ProgrammingRead, dependencies=[Depends(require_roles(["admin", "planner"]))])
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

# Eliminar programación (solo admin/planner)
@router.delete("/{programming_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["admin", "planner"]))])
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
    # Solo admin/planner pueden crear
    if current_user.role.value not in ("admin", "planner"):
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
    if current_user.role.value not in ("admin", "planner"):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task not in programming.tasks:
        programming.tasks.append(task)
        db.commit()
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
    if current_user.role.value not in ("admin", "planner"):
        raise HTTPException(status_code=403, detail="Not authorized")
    task = db.query(Task).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task in programming.tasks:
        programming.tasks.remove(task)
        db.commit()
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
    current_user=Depends(require_roles(["admin", "planner"]))
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
        # Si se reciben start_time y end_time, usarlos
        if item.start_time and item.end_time:
            pt.start_time = item.start_time if isinstance(item.start_time, datetime) else datetime.fromisoformat(item.start_time)
            pt.end_time = item.end_time if isinstance(item.end_time, datetime) else datetime.fromisoformat(item.end_time)
            current_time = pt.end_time
        else:
            # Si no, calcular como antes
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