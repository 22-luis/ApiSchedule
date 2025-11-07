import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.services.timer import TimerService
from app.schemas.stopwatch import Stopwatch as StopwatchSchema
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from app.schemas.record_stopwatch import RecordStopwatch as RecordStopwatchSchema

class RecordStopwatchDetailSchema(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    quantity: float
    accumulated_duration: float
    creation_date: datetime
    code_code: str
    task_description: str
    task_type: Optional[str] = None
    task_activity: Optional[str] = None
    task_people: int

router = APIRouter()

class TaskStatusRequest(BaseModel):
    task_ids: List[uuid.UUID]

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    record_id: Optional[str] = None
    is_from_programming: bool

class TimerStartPayload(BaseModel):
    start_time: Optional[datetime] = None
    is_from_programming: bool = False

class TimerStopPayload(BaseModel):
    quantity: float

@router.post("/stopwatch/start/{task_id}", response_model=StopwatchSchema, tags=["Timer"])
def start_timer(task_id: uuid.UUID, payload: TimerStartPayload, db: Session = Depends(get_db)):
    timer_service = TimerService(db)
    try:
        stopwatch = timer_service.start_stopwatch(
            task_id=task_id,
            start_time=payload.start_time,
            is_from_programming=payload.is_from_programming
        )
        return stopwatch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/stop/{task_id}", response_model=RecordStopwatchSchema, tags=["Timer"])
def stop_timer(task_id: uuid.UUID, payload: TimerStopPayload, db: Session = Depends(get_db)):
    timer_service = TimerService(db)
    try:
        record = timer_service.stop_stopwatch(task_id=task_id, real_quantity=payload.quantity)
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/pause/{task_id}", response_model=StopwatchSchema, tags=["Timer"])
def pause_timer(task_id: uuid.UUID, db: Session = Depends(get_db)):
    timer_service = TimerService(db)
    try:
        stopwatch = timer_service.pause_stopwatch(task_id=task_id)
        return stopwatch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/resume/{task_id}", response_model=StopwatchSchema, tags=["Timer"])
def resume_timer(task_id: uuid.UUID, db: Session = Depends(get_db)):
    timer_service = TimerService(db)
    try:
        stopwatch = timer_service.resume_stopwatch(task_id=task_id)
        return stopwatch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/status", response_model=List[TaskStatusResponse], tags=["Timer"])
def get_tasks_status(payload: TaskStatusRequest, db: Session = Depends(get_db)):
    timer_service = TimerService(db)
    try:
        statuses = timer_service.get_tasks_status(payload.task_ids)
        return statuses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stopwatch/records/daily", response_model=List[RecordStopwatchDetailSchema], tags=["Timer"])
def get_daily_records(db: Session = Depends(get_db)):
    timer_service = TimerService(db)
    try:
        daily_records = timer_service.get_daily_record_stopwatches()
        return daily_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stopwatch/records/all", response_model=List[RecordStopwatchDetailSchema], tags=["Timer"])
def get_all_records(db: Session = Depends(get_db)):
    timer_service = TimerService(db)
    try:
        all_records = timer_service.get_all_record_stopwatches()
        return all_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
