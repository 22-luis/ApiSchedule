from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from uuid import UUID
from app.modules.programming.models.task import Task
from app.modules.programming.models.programming import ProgrammingTask

def find_all(db: Session) -> List[Task]:
    return db.query(Task).all()

def find_by_id(db: Session, task_id: str) -> Optional[Task]:
    return db.query(Task).get(task_id)

def find_with_relations(db: Session, task_id: str) -> Optional[Task]:
    return db.query(Task).options(
        joinedload(Task.code),
        joinedload(Task.preparation),
        joinedload(Task.teams),
        joinedload(Task.created_by_user)
    ).filter(Task.id == task_id).first()

def save(db: Session, task: Task) -> Task:
    db.add(task)
    db.flush()
    return task

def delete(db: Session, task: Task):
    db.delete(task)

def find_programming_task(db: Session, programming_id: UUID, task_id: UUID) -> Optional[ProgrammingTask]:
    return db.query(ProgrammingTask).filter_by(
        programming_id=programming_id, 
        task_id=task_id
    ).first()

def find_programming_task_by_task_id(db: Session, task_id: UUID) -> Optional[ProgrammingTask]:
    return db.query(ProgrammingTask).filter_by(
        task_id=task_id
    ).order_by(ProgrammingTask.created_at.desc()).first()

def save_programming_task(db: Session, pt: ProgrammingTask) -> ProgrammingTask:
    db.add(pt)
    return pt

def commit(db: Session):
    db.commit()
