from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from datetime import date
from app.modules.programming.models.programming import Programming, ProgrammingTask
from app.modules.programming.models.task import Task

def find_all(db: Session) -> List[Programming]:
    return db.query(Programming).all()

def find_by_team_ids(db: Session, team_ids: List[str]) -> List[Programming]:
    return db.query(Programming).filter(Programming.team_id.in_(team_ids)).all()

def find_by_team_and_date(db: Session, team_id: str, date_obj: date) -> Optional[Programming]:
    return db.query(Programming).options(
        joinedload(Programming.programming_tasks).joinedload(ProgrammingTask.task).joinedload(Task.teams)
    ).filter_by(team_id=team_id, date=date_obj).first()

def find_by_id(db: Session, programming_id: UUID) -> Optional[Programming]:
    return db.query(Programming).get(programming_id)

def save(db: Session, programming: Programming) -> Programming:
    db.add(programming)
    db.commit()
    db.refresh(programming)
    return programming

def commit(db: Session):
    db.commit()
