import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.modules.timer.services import timer_service
from app.modules.timer.schemas.stopwatch import Stopwatch as StopwatchSchema
from typing import List, Union

from app.modules.timer.schemas.record_stopwatch import RecordStopwatch as RecordStopwatchSchema
from app.modules.programming.schemas.programming import ProgrammingTaskOrderOut as ProgrammingTaskSchema

from app.shared.utils.core.dependencies import get_current_user
from app.modules.organization.models.user import User

from app.modules.timer.schemas.timer import (
    RecordStopwatchDetailSchema,
    TaskStatusRequest,
    TaskStatusResponse,
    TimerStartPayload,
    TimerStopPayload
)

router = APIRouter()

@router.post("/stopwatch/start/{task_id}", response_model=StopwatchSchema, tags=["Timer"])
def start_timer(task_id: uuid.UUID, payload: TimerStartPayload, db: Session = Depends(get_db)):
    timer_service.db = db
    try:
        stopwatch = timer_service.start_stopwatch(
            task_id=task_id,
            start_time=payload.start_time,
            is_from_programming=payload.is_from_programming
        )
        return stopwatch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/stop/{task_id}", response_model=Union[RecordStopwatchSchema, ProgrammingTaskSchema], tags=["Timer"])
def stop_timer(task_id: uuid.UUID, payload: TimerStopPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    timer_service.db = db
    try:
        record = timer_service.stop_stopwatch(task_id=task_id, real_quantity=payload.quantity, user_id=current_user.id, is_completed=payload.is_completed)
        return record
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/pause/{task_id}", response_model=StopwatchSchema, tags=["Timer"])
def pause_timer(task_id: uuid.UUID, db: Session = Depends(get_db)):
    timer_service.db = db
    try:
        stopwatch = timer_service.pause_stopwatch(task_id=task_id)
        return stopwatch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/resume/{task_id}", response_model=StopwatchSchema, tags=["Timer"])
def resume_timer(task_id: uuid.UUID, db: Session = Depends(get_db)):
    timer_service.db = db
    try:
        stopwatch = timer_service.resume_stopwatch(task_id=task_id)
        return stopwatch
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stopwatch/status", response_model=List[TaskStatusResponse], tags=["Timer"])
def get_tasks_status_programming(payload: TaskStatusRequest, db: Session = Depends(get_db)):
    timer_service.db = db
    try:
        statuses = timer_service.get_tasks_status(payload.task_ids)
        return statuses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stopwatch/status/timer", response_model=List[TaskStatusResponse], tags=["Timer"])
def get_tasks_status_manual(payload: TaskStatusRequest, db: Session = Depends(get_db)):
    timer_service.db = db
    try:
        statuses = timer_service.get_tasks_status_not_programmed(payload.task_ids)
        return statuses
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stopwatch/records/daily", response_model=List[RecordStopwatchDetailSchema], tags=["Timer"])
def get_daily_records(db: Session = Depends(get_db)):
    timer_service.db = db
    try:
        daily_records = timer_service.get_daily_record_stopwatches()
        return daily_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stopwatch/records/all", response_model=List[RecordStopwatchDetailSchema], tags=["Timer"])
def get_all_records(db: Session = Depends(get_db)):
    timer_service.db = db
    try:
        all_records = timer_service.get_all_record_stopwatches()
        return all_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
