from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.models.task import Task
from app.models.record_stopwatch import RecordStopwatch
from app.schemas.record_stopwatch import RecordStopwatchCreate, RecordStopwatchUpdate
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/start_stopwatch/{task_id}", response_model=RecordStopwatch)
def start_stopwatch(task_id: uuid.UUID, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if a stopwatch is already running for this task
    existing_record = db.query(RecordStopwatch).filter(RecordStopwatch.code == task.code.code, RecordStopwatch.end_time == None).first()
    if existing_record:
        raise HTTPException(status_code=400, detail="Stopwatch already started for this task")

    record = RecordStopwatch(
        lote=task.lote,
        code=task.code.code,
        description=task.description,
        people=task.people,
        quantity=task.quantity,
        start_time=datetime.utcnow(),
        real_quantity=0 # Initial value
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.put("/stop_stopwatch/{record_id}", response_model=RecordStopwatch)
def stop_stopwatch(record_id: uuid.UUID, record_update: RecordStopwatchUpdate, db: Session = Depends(get_db)):
    record = db.query(RecordStopwatch).filter(RecordStopwatch.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if record.end_time:
        raise HTTPException(status_code=400, detail="Stopwatch already stopped")

    record.end_time = record_update.end_time
    record.real_quantity = record_update.real_quantity
    db.commit()
    db.refresh(record)
    return record
