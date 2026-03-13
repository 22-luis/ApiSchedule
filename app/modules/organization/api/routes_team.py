import uuid
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.organization.schemas.team import TeamCreate, TeamOut, TeamUpdate, TeamMembersUpdate
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_active_user, require_roles
from app.modules.organization.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])

@router.get("/", response_model=List[TeamOut])
def get_teams(
    target_date: date = Query(default=date.today()),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user)
):
    return TeamService.get_all_teams(db, target_date)

@router.post("/", response_model=TeamOut)
def create_team(
    team_in: TeamCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return TeamService.create_team(db, team_in)

@router.patch("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: uuid.UUID,
    team_update: TeamUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    from app.modules.organization.repositories import team_repository
    team = team_repository.find_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team_update.name is not None:
        team.name = team_update.name
    if team_update.supervisorId is not None:
        team.supervisorId = team_update.supervisorId
        
    db.commit()
    db.refresh(team)
    return TeamService._build_team_out(db, team, date.today())

@router.put("/{team_id}/members", response_model=TeamOut)
def update_team_members(
    team_id: uuid.UUID,
    update_data: TeamMembersUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    result = TeamService.update_team_members(db, team_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="Team not found")
    return result

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    from app.modules.organization.repositories import team_repository
    team = team_repository.find_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team_repository.delete_team(db, team)
    return None
