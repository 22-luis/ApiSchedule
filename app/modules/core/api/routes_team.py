import uuid
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.modules.core.models.role import UserRole
from app.modules.core.models.team import Team, UserTeam
from app.modules.core.models.user import User
from app.modules.core.schemas.team import TeamCreate, TeamOut, TeamUpdate, TeamMembersUpdate, TeamMemberOut
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_active_user, require_roles

router = APIRouter(prefix="/teams", tags=["teams"])


def _build_team_out(db: Session, team: Team, target_date: date) -> TeamOut:
    """Helper para construir el esquema TeamOut filtrando miembros por fecha."""
    active_members_map = {}
    for association in team.member_associations:
        if association.start_date <= target_date and (
                association.end_date is None or association.end_date >= target_date):
            if association.user_id not in active_members_map:
                active_members_map[association.user_id] = TeamMemberOut(
                    userId=association.user_id,
                    username=association.user.username if association.user else None,
                    startDate=association.start_date,
                    endDate=association.end_date
                )

    supervisor = db.query(User).filter(User.id == team.supervisorId).first()

    return TeamOut(
        id=team.id,
        name=team.name,
        supervisorId=team.supervisorId,
        supervisorUsername=supervisor.username if supervisor else None,
        members=list(active_members_map.values())
    )

@router.get("/", response_model=List[TeamOut])
def get_teams(
    target_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_active_user)
):
    teams = db.query(Team).all()

    result = []
    for team in teams:
        # Filter members for the specific date
        active_members_map = {}
        for association in team.member_associations:
            # Check if the association covers the target_date
            # start_date <= target_date AND (end_date IS NULL OR end_date >= target_date)

            if association.start_date <= target_date and (association.end_date is None or association.end_date >= target_date):
                # Deduplicate by user_id. If multiple records exist, we take the first one encountered.
                if association.user_id not in active_members_map:
                    member_out = TeamMemberOut(
                        userId=association.user_id,
                        username=association.user.username if association.user else None,
                        startDate=association.start_date,
                        endDate=association.end_date
                    )
                    active_members_map[association.user_id] = member_out

        active_members = list(active_members_map.values())

        supervisor_username = None
        # We need to fetch supervisor manually or via relationship if not loaded
        supervisor = db.query(User).filter(User.id == team.supervisorId).first()
        if supervisor:
            supervisor_username = supervisor.username

        team_out = TeamOut(
            id=team.id,
            name=team.name,
            supervisorId=team.supervisorId,
            supervisorUsername=supervisor_username,
            members=active_members
        )
        result.append(team_out)

    return result

@router.post("/", response_model=TeamOut)
def create_team(
    team_in: TeamCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    team = Team(
        name=team_in.name,
        supervisorId=team_in.supervisorId
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Add initial members if any (starting today)
    today = date.today()
    if team_in.members:
        for member_config in team_in.members:
            user_team = UserTeam(
                user_id=member_config.userId,
                team_id=team.id,
                start_date=member_config.startDate or today,
                end_date=member_config.endDate
            )
            db.add(user_team)
        db.commit()
        db.refresh(team)

    # Construct response
    return _build_team_out(db, team, today)

@router.patch("/{team_id}", response_model=TeamOut)
def update_team(
    team_id: uuid.UUID,
    team_update: TeamUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team_update.name is not None:
        team.name = team_update.name
    if team_update.supervisorId is not None:
        team.supervisorId = team_update.supervisorId
        
    db.commit()
    db.refresh(team)
    return _build_team_out(db, team, date.today())

@router.put("/{team_id}/members", response_model=TeamOut)
def update_team_members(
    team_id: uuid.UUID,
    update_data: TeamMembersUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
        
    target_date = update_data.date
    new_member_ids = set(update_data.userIds)
    
    # Get current active associations for this team on the target date
    current_associations = []
    for assoc in team.member_associations:
        # Check if active on target_date
        if assoc.start_date <= target_date and (assoc.end_date is None or assoc.end_date >= target_date):
            current_associations.append(assoc)
            
    current_member_ids = {assoc.user_id for assoc in current_associations}
    
    for assoc in current_associations:
        if assoc.user_id not in new_member_ids:
            # End their membership yesterday
            end_date = target_date - timedelta(days=1)
            
            if assoc.start_date > end_date:
                # If start_date >= target_date, delete it.
                db.delete(assoc)
            else:
                assoc.end_date = end_date
                
    for user_id in new_member_ids:
        if user_id not in current_member_ids:
            new_assoc = UserTeam(
                user_id=user_id,
                team_id=team.id,
                start_date=target_date,
                end_date=None
            )
            db.add(new_assoc)
            
    db.commit()
    db.refresh(team)
    
    return _build_team_out(db, team, target_date)

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN))
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    db.delete(team)
    db.commit()
    return None
