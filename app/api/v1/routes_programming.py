from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List
from app.models.programming import Programming, programming_task
from app.models.task import Task
from app.models.team import Team
from app.schemas.programming import ProgrammingCreate, ProgrammingRead, ProgrammingUpdate
from app.db.dependency import get_db
from app.utils.dependencies import get_current_user, require_roles
from datetime import date, datetime
from uuid import UUID

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
@router.get("/by_team_date", response_model=ProgrammingRead)
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
        response = {
            "id": programming.id,
            "date": programming.date,
            "team_id": str(programming.team_id) if not isinstance(programming.team_id, UUID) else programming.team_id,
            "tasks": [str(t.id) if not isinstance(t.id, UUID) else t.id for t in programming.tasks]
        }
        print("[DEBUG] response to return:", response)
        return response
    except Exception as e:
        print("[DEBUG] Exception in get_programming_by_team_date:", e)
        raise

# Obtener una programación
@router.get("/{programming_id}", response_model=ProgrammingRead)
def get_programming(programming_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if current_user.role not in ("admin", "planner") and not user_belongs_to_team(current_user, programming.team_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return programming

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
def update_programming(programming_id: int, data: ProgrammingUpdate, db: Session = Depends(get_db)):
    programming = db.query(Programming).get(programming_id)
    if not programming:
        raise HTTPException(status_code=404, detail="Programming not found")
    if data.task_ids is not None:
        programming.tasks = db.query(Task).filter(Task.id.in_(data.task_ids)).all()
    db.commit()
    db.refresh(programming)
    return programming

# Eliminar programación (solo admin/planner)
@router.delete("/{programming_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_roles(["admin", "planner"]))])
def delete_programming(programming_id: int, db: Session = Depends(get_db)):
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
    programming_id: int,
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
    return programming 

@router.post("/{programming_id}/remove_task", response_model=ProgrammingRead)
def remove_task_from_programming(
    programming_id: int,
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
    return programming 