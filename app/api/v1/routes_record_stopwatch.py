from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.models.task import Task
from app.models.record_stopwatch import RecordStopwatch as RecordStopwatchModel
from app.schemas.record_stopwatch import RecordStopwatch, RecordStopwatchUpdate, RecordStopwatchStart
from datetime import datetime
import uuid

router = APIRouter()

@router.post("/start_stopwatch/{task_id}", response_model=RecordStopwatch)
def start_stopwatch(task_id: uuid.UUID, payload: RecordStopwatchStart, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    existing_record = db.query(RecordStopwatchModel).filter(RecordStopwatchModel.code == task.code.code, RecordStopwatchModel.end_time == None).first()
    if existing_record:
        raise HTTPException(status_code=400, detail="Stopwatch already started for this task")

    start_time = payload.start_time if payload and payload.start_time else datetime.utcnow()

    record = RecordStopwatchModel(
        lote=task.lote,
        code=task.code.code,
        description=task.description,
        people=task.people,
        quantity=task.quantity,
        start_time=start_time,
        real_quantity=0,
        accumulated_duration=0,
        is_paused=False
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router.put("/pause_stopwatch/{record_id}", response_model=RecordStopwatch)
def pause_stopwatch(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.query(RecordStopwatchModel).filter(RecordStopwatchModel.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if record.is_paused:
        raise HTTPException(status_code=400, detail="Stopwatch is already paused")
    if record.end_time:
        raise HTTPException(status_code=400, detail="Stopwatch is already stopped")

    elapsed_seconds = (datetime.utcnow() - record.start_time).total_seconds()
    record.accumulated_duration += int(elapsed_seconds)
    record.is_paused = True
    db.commit()
    db.refresh(record)
    return record

@router.put("/resume_stopwatch/{record_id}", response_model=RecordStopwatch)
def resume_stopwatch(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.query(RecordStopwatchModel).filter(RecordStopwatchModel.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if not record.is_paused:
        raise HTTPException(status_code=400, detail="Stopwatch is not paused")

    record.is_paused = False
    record.start_time = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record

@router.put("/stop_stopwatch/{record_id}", response_model=RecordStopwatch)
def stop_stopwatch(record_id: uuid.UUID, record_update: RecordStopwatchUpdate, db: Session = Depends(get_db)):
    record = db.query(RecordStopwatchModel).filter(RecordStopwatchModel.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    if record.end_time:
        raise HTTPException(status_code=400, detail="Stopwatch already stopped")

    if not record.is_paused:
        elapsed_seconds = (datetime.utcnow() - record.start_time).total_seconds()
        record.accumulated_duration += int(elapsed_seconds)

    record.end_time = record_update.end_time
    record.real_quantity = record_update.real_quantity
    record.is_paused = False
    db.commit()
    db.refresh(record)
    return record
