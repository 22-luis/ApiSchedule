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

router = APIRouter()

@router.post("/teams", response_model=TeamOut)
def create_team(team: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    supervisor = db.query(User).filter(User.id == team.supervisorId, User.state == UserState.ACTIVE).first()
    if not supervisor:
        raise HTTPException(status_code=400, detail="Supervisor must be an active user")
    db_team = Team(name=team.name, supervisorId=team.supervisorId)
    # Asign active members
    if team.userIds:
        active_users = db.query(User).filter(User.id.in_(team.userIds), User.state == UserState.ACTIVE).first()
        db_team.users = active_users
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team

@router.delete("/teams/{team_id}", response_model=TeamOut)
def delete_team(team_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    db.delete(db_team)
    db.commit()
    return {"message": "Team deleted successfully"}

@router.patch("/teams/{team_id}", response_model=TeamOut)
def update_team(team_id: str, team: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    db_team.name = team.name
    
    supervisor = db.query(User).filter(User.id == team.supervisorId, User.state == UserState.ACTIVE).first()
    if not supervisor:
        raise HTTPException(status_code=400, detail="Supervisor must be an active user")
    db_team.supervisorId = team.supervisorId
    
    if team.userIds is not None:  # user_ids es la lista de IDs de usuarios a asignar
        active_users = db.query(User).filter(User.id.in_(team.userIds), User.state == UserState.ACTIVE).all()
        db_team.users = active_users
    
    db.commit()
    db.refresh(db_team)
    return db_team

@router.get("/teams", response_model=List[TeamOut])
def get_teams(db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))):
    teams = db.query(Team).all()
    return teams

@router.get("/teams/{team_id}", response_model=TeamOut)
def get_team(team_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
    # Filtra solo usuarios activos
    db_team.users = [user for user in db_team.users if user.state == UserState.ACTIVE]
    return db_team