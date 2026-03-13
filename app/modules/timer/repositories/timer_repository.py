from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid
from datetime import datetime

from app.modules.timer.models.stopwatch import Stopwatch
from app.modules.timer.models.record_stopwatch import RecordStopwatch
from app.modules.timer.models.state import TimerStatus
from app.modules.programming.models.task import Task
from app.modules.codes.models.code import Code

def find_stopwatch_by_task(db: Session, task_id: uuid.UUID, is_from_programming: bool = False) -> Optional[Stopwatch]:
    return db.query(Stopwatch).filter(
        Stopwatch.task_id == task_id,
        Stopwatch.is_from_programming == is_from_programming
    ).first()

def find_running_stopwatch(db: Session, task_id: uuid.UUID) -> Optional[Stopwatch]:
    return db.query(Stopwatch).filter(
        Stopwatch.task_id == task_id,
        Stopwatch.status == TimerStatus.RUNNING
    ).first()

def find_paused_stopwatch(db: Session, task_id: uuid.UUID) -> Optional[Stopwatch]:
    return db.query(Stopwatch).filter(
        Stopwatch.task_id == task_id,
        Stopwatch.status == TimerStatus.PAUSED
    ).first()

def find_stopwatch_by_task_any_status(db: Session, task_id: uuid.UUID) -> Optional[Stopwatch]:
    return db.query(Stopwatch).filter(Stopwatch.task_id == task_id).first()

def find_stopwatches_by_task_ids(db: Session, task_ids: List[uuid.UUID], is_from_programming: bool = True) -> List[Stopwatch]:
    return db.query(Stopwatch).filter(
        Stopwatch.task_id.in_(task_ids),
        Stopwatch.is_from_programming == is_from_programming
    ).all()

def save_stopwatch(db: Session, stopwatch: Stopwatch) -> Stopwatch:
    db.add(stopwatch)
    db.commit()
    db.refresh(stopwatch)
    return stopwatch

def delete_stopwatch(db: Session, stopwatch: Stopwatch):
    db.delete(stopwatch)
    db.commit()

def save_record_stopwatch(db: Session, record: RecordStopwatch) -> RecordStopwatch:
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def find_record_by_task(db: Session, task_id: uuid.UUID) -> Optional[RecordStopwatch]:
    return db.query(RecordStopwatch).filter(RecordStopwatch.task_id == task_id).first()

def find_record_by_id(db: Session, record_id: uuid.UUID) -> Optional[RecordStopwatch]:
    return db.query(RecordStopwatch).filter(RecordStopwatch.id == record_id).first()

def find_records_by_task_ids(db: Session, task_ids: List[uuid.UUID]) -> List[RecordStopwatch]:
    return db.query(RecordStopwatch).filter(RecordStopwatch.task_id.in_(task_ids)).all()

def find_daily_records_with_details(db: Session, date_target: datetime.date) -> List[tuple]:
    return db.query(
        RecordStopwatch,
        Code.code,
        Task.description,
        Task.type,
        Task.activity,
        Task.people,
        Code.activity.label("code_activity"),
        Code.type.label("code_type")
    ).join(Task, RecordStopwatch.task_id == Task.id).join(Code, Task.code_id == Code.id).filter(
        func.date(RecordStopwatch.creation_date) == date_target
    ).all()

def find_all_records_with_details(db: Session) -> List[tuple]:
    return db.query(
        RecordStopwatch,
        Code.code,
        Task.description,
        Task.type,
        Task.activity,
        Task.people,
        Code.activity.label("code_activity"),
        Code.type.label("code_type")
    ).join(Task, RecordStopwatch.task_id == Task.id).join(Code, Task.code_id == Code.id).all()
