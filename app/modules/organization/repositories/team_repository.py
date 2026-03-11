from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from app.modules.organization.models.team import Team, UserTeam

def find_all_teams(db: Session) -> List[Team]:
    """Obtiene todos los equipos."""
    return db.query(Team).all()

def find_team_by_id(db: Session, team_id: uuid.UUID) -> Optional[Team]:
    """Busca un equipo por ID."""
    return db.query(Team).filter(Team.id == team_id).first()

def find_user_team_association(db: Session, user_id: uuid.UUID, team_id: uuid.UUID) -> Optional[UserTeam]:
    """Busca una asociación específica entre usuario y equipo."""
    return db.query(UserTeam).filter(
        UserTeam.user_id == user_id,
        UserTeam.team_id == team_id
    ).first()

def save_team(db: Session, team: Team) -> Team:
    """Guarda un equipo."""
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

def delete_team(db: Session, team: Team) -> None:
    """Elimina un equipo."""
    db.delete(team)
    db.commit()

def add_association(db: Session, association: UserTeam) -> UserTeam:
    """Guarda una asociación UserTeam."""
    db.add(association)
    db.commit()
    return association

def delete_association(db: Session, association: UserTeam) -> None:
    """Elimina una asociación UserTeam."""
    db.delete(association)
    db.commit()
