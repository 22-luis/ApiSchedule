"""
Rutas de la API para la gestión de códigos predefinidos: creación, actualización, eliminación, consulta con paginación, búsqueda y carga masiva.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.models.code import Code
from app.models.team import Team
from app.schemas.code import CodeCreate, CodeUpdate, CodeOut, CodePageOut
from app.db.dependency import get_db
from app.models.user import User
from app.utils.dependencies import require_roles
from app.models.role import UserRole
import uuid
from app.models.task import Task
from app.models.order import Order

router = APIRouter(prefix="/codes", tags=["codes"])

def team_to_dict(team, db):
    supervisor = db.query(User).filter(User.id == team.supervisorId).first()
    supervisor_username = supervisor.username if supervisor else None
    return {
        "id": team.id,
        "name": team.name,
        "supervisorId": team.supervisorId,
        "supervisorUsername": supervisor_username,
        "users": team.users,
    }

def clean_float(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace('\xa0', '').replace(' ', '')
        if value == '' or value == '-':
            return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def clean_str(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value)

@router.post("/", response_model=CodeOut)
def create_code(code: CodeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_code = Code(
        code=code.code,
        description=code.description,
        unit=code.unit,
        type=code.type,
        activity=code.activity,
        quantity=code.quantity,
        time=code.time,
        people=code.people,
        performance=code.performance,
        material=code.material,
        presentation=code.presentation,
        fabricationCode=code.fabricationCode,
        usefulLife=code.usefulLife,
        related_code_team=code.related_code_team
    )
    if code.teamIds:
        teams = db.query(Team).filter(Team.id.in_(code.teamIds)).all()
        db_code.teams = teams
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    teams = [team_to_dict(t, db) for t in db_code.teams]
    return {
        "id": db_code.id,
        "code": db_code.code,
        "description": db_code.description,
        "unit": db_code.unit,
        "type": db_code.type,
        "activity": db_code.activity,
        "quantity": db_code.quantity,
        "time": db_code.time,
        "people": db_code.people,
        "performance": db_code.performance,
        "material": db_code.material,
        "presentation": db_code.presentation,
        "fabricationCode": db_code.fabricationCode,
        "usefulLife": db_code.usefulLife,
        "related_code_team": db_code.related_code_team,
        "teams": teams,
    }

@router.post("/bulk_upload")
def bulk_upload_codes(codes: list[dict], db: Session = Depends(get_db), current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    created = 0
    errors = []
    for idx, code_data in enumerate(codes):
        code_str = code_data.get("code")
        description = code_data.get("description")
        if not code_str or not description:
            errors.append({"row": idx+1, "error": "Falta código o descripción"})
            continue
        # Verifica duplicados
        exists = db.query(Code).filter(Code.code == code_str).first()
        if exists:
            errors.append({"row": idx+1, "error": f"Código duplicado: {code_str}"})
            continue
        db_code = Code(
            code=clean_str(code_str),
            description=clean_str(description),
            unit=clean_str(code_data.get("unit")),
            type=clean_str(code_data.get("type")),
            activity=clean_str(code_data.get("activity")),
            quantity=clean_float(code_data.get("quantity")),
            time=clean_float(code_data.get("time")),
            people=clean_float(code_data.get("people")),
            performance=clean_float(code_data.get("performance")),
            material=clean_str(code_data.get("material")),
            presentation=clean_str(code_data.get("presentation")),
            fabricationCode=clean_str(code_data.get("fabricationCode")),
            usefulLife=clean_str(code_data.get("usefulLife")),
            related_code_team=clean_str(code_data.get("related_code_team"))
        )
        db.add(db_code)
        created += 1
    db.commit()
    return {"created": created, "errors": errors}

@router.get("/", response_model=CodePageOut)
def get_codes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de registros a devolver"),
    search: str = Query(None, description="Buscar por código o descripción"),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    query = db.query(Code)
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.filter(
            (Code.code.ilike(search_pattern)) |
            (Code.description.ilike(search_pattern))
        )
    total = query.count()
    codes = query.offset(skip).limit(limit).all()
    result = []
    for c in codes:
        teams = [team_to_dict(t, db) for t in c.teams]
        result.append({
            "id": c.id,
            "code": clean_str(c.code),
            "description": clean_str(c.description),
            "unit": clean_str(c.unit),
            "type": clean_str(c.type),
            "activity": clean_str(c.activity),
            "quantity": c.quantity,
            "time": c.time,
            "people": c.people,
            "performance": c.performance,
            "material": clean_str(c.material),
            "presentation": clean_str(c.presentation),
            "fabricationCode": clean_str(c.fabricationCode),
            "usefulLife": clean_str(c.usefulLife),
            "related_code_team": clean_str(c.related_code_team),
            "teams": teams,
        })
    return {"codes": result, "total": total}

@router.get("/by_code_and_activity")
def get_code_by_code_and_activity(code: str, activity: str, db: Session = Depends(get_db)):
    code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
    if not code_obj:
        raise HTTPException(status_code=404, detail="Code not found with given code and activity")
    return code_obj

@router.get("/by_code/{code}/activity")
def get_code_activity(code: str, db: Session = Depends(get_db)):
    code_obj = db.query(Code).filter(Code.code == code).first()
    if not code_obj:
        raise HTTPException(status_code=404, detail="Code not found")
    return {
        "code": code,
        "activity": getattr(code_obj, "activity", None)
    }

@router.get("/by_code/{code}/lotes")
def get_lotes_by_code(code: str, db: Session = Depends(get_db)):
    lotes = db.query(Order.lote).filter(Order.code == code).all()
    if not lotes:
        raise HTTPException(status_code=404, detail="No lotes found for this code")
    return {
        "code": code,
        "lotes": [l[0] for l in lotes if l[0] is not None]
    }

@router.get("/{code_id}", response_model=CodeOut)
def get_code(code_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    teams = [team_to_dict(t, db) for t in code.teams]
    return {
        "id": code.id,
        "code": code.code,
        "description": code.description,
        "unit": code.unit,
        "type": code.type,
        "activity": code.activity,
        "quantity": code.quantity,
        "time": code.time,
        "people": code.people,
        "performance": code.performance,
        "material": code.material,
        "presentation": code.presentation,
        "fabricationCode": code.fabricationCode,
        "usefulLife": code.usefulLife,
        "related_code_team": code.related_code_team,
        "teams": teams,
    }

@router.patch("/{code_id}", response_model=CodeOut)
def update_code(code_id: uuid.UUID, code_update: CodeUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    update_data = code_update.dict(exclude_unset=True)
    team_ids = update_data.pop("teamIds", None)
    for field, value in update_data.items():
        setattr(db_code, field, value)
    if team_ids is not None:
        teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
        db_code.teams = teams
    db.commit()
    db.refresh(db_code)
    teams = [team_to_dict(t, db) for t in db_code.teams]
    return {
        "id": db_code.id,
        "code": db_code.code,
        "description": db_code.description,
        "unit": db_code.unit,
        "type": db_code.type,
        "activity": db_code.activity,
        "quantity": db_code.quantity,
        "time": db_code.time,
        "people": db_code.people,
        "performance": db_code.performance,
        "material": db_code.material,
        "presentation": db_code.presentation,
        "fabricationCode": db_code.fabricationCode,
        "usefulLife": db_code.usefulLife,
        "related_code_team": db_code.related_code_team,
        "teams": teams,
    }

@router.delete("/{code_id}")
def delete_code(code_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    db.delete(db_code)
    db.commit()
    return {"message": "Code deleted successfully"} 