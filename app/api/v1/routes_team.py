"""
Rutas de la API para la gestión de equipos: creación, actualización, eliminación y consulta con manejo de supervisores y miembros.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.models import team
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from typing import List, Optional
from app.models.user import User
from app.models.team import Team
from app.models.state import UserState
from app.schemas.team import TeamCreate, TeamOut
from app.utils.dependencies import get_current_user, require_roles
from app.models.role import UserRole
from app.core.task_config import get_most_suitable_weighing_team

router = APIRouter(prefix="/teams", tags=["teams"])

@router.post("/", response_model=TeamOut)
def create_team(team: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    supervisor = db.query(User).filter(User.id == team.supervisorId, User.state == UserState.ACTIVE).all()
    if not supervisor:
        raise HTTPException(status_code=400, detail="Supervisor must be an active user")
    db_team = Team(name=team.name, supervisorId=team.supervisorId)
    # Asign active members
    if team.userIds:
        active_users = db.query(User).filter(User.id.in_(team.userIds), User.state == UserState.ACTIVE).all()
        db_team.users = active_users
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    supervisor = db.query(User).filter(User.id == db_team.supervisorId).first()
    supervisor_username = supervisor.username if supervisor else None
    return {
        "id": db_team.id,
        "name": db_team.name,
        "supervisorId": db_team.supervisorId,
        "supervisorUsername": supervisor_username,
        "users": db_team.users,
    }

@router.delete("/{team_id}", response_model=TeamOut)
def delete_team(team_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    supervisor = db.query(User).filter(User.id == db_team.supervisorId).first()
    supervisor_username = supervisor.username if supervisor else None
    users = db_team.users
    response = {
        "id": db_team.id,
        "name": db_team.name,
        "supervisorId": db_team.supervisorId,
        "supervisorUsername": supervisor_username,
        "users": users,
    }
    db.delete(db_team)
    db.commit()
    return response

@router.patch("/{team_id}", response_model=TeamOut)
def update_team(team_id: str, team: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    supervisor = db.query(User).filter(User.id == team.supervisorId, User.state == UserState.ACTIVE).first()
    if not supervisor:
        raise HTTPException(status_code=400, detail="Supervisor must be an active user")

    # Actualizar campos del equipo
    setattr(db_team, 'name', team.name)
    setattr(db_team, 'supervisorId', team.supervisorId)

    if team.userIds is not None:  # user_ids es la lista de IDs de usuarios a asignar
        active_users = db.query(User).filter(User.id.in_(team.userIds), User.state == UserState.ACTIVE).all()
        db_team.users = active_users

    db.commit()
    db.refresh(db_team)
    supervisor = db.query(User).filter(User.id == db_team.supervisorId).first()
    supervisor_username = supervisor.username if supervisor else None
    return {
        "id": db_team.id,
        "name": db_team.name,
        "supervisorId": db_team.supervisorId,
        "supervisorUsername": supervisor_username,
        "users": db_team.users,
    }

@router.get("/", response_model=List[TeamOut])
def get_teams(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from app.models.role import UserRole
    if current_user.role in (UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR):
        teams = db.query(Team).all()
    else:
        teams = getattr(current_user, 'teams', [])
    result = []
    for t in teams:
        supervisor = db.query(User).filter(User.id == t.supervisorId).first()
        supervisor_username = supervisor.username if supervisor else None
        result.append({
            "id": t.id,
            "name": t.name,
            "supervisorId": t.supervisorId,
            "supervisorUsername": supervisor_username,
            "users": t.users
        })
    return result

@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    supervisor = db.query(User).filter(User.id == db_team.supervisorId).first()
    supervisor_username = supervisor.username if supervisor else None
    # Filtra solo usuarios activos
    users = [user for user in db_team.users if user.state == UserState.ACTIVE]
    return {
        "id": db_team.id,
        "name": db_team.name,
        "supervisorId": db_team.supervisorId,
        "supervisorUsername": supervisor_username,
        "users": users
    }


@router.get("/weighing/most-suitable")
def get_most_suitable_weighing_team_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Obtiene el equipo más idóneo para actividades de pesado.
    
    Returns:
        Información del equipo más idóneo para pesado con ID y nombre
    """
    try:
        print(f"[DEBUG] get_most_suitable_weighing_team_endpoint: Iniciando búsqueda de equipo más idóneo para pesado")
        
        result = get_most_suitable_weighing_team(db)
        
        print(f"[DEBUG] get_most_suitable_weighing_team_endpoint: Resultado obtenido - {result}")
        
        return result
        
    except Exception as e:
        print(f"[DEBUG] get_most_suitable_weighing_team_endpoint: Error - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo equipo más idóneo para pesado: {str(e)}")