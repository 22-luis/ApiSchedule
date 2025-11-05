from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.dependency import get_db
from app.services.timer import TimerService
import uuid

from typing import Optional
from app.schemas.record_stopwatch import RecordStopwatch as RecordStopwatchSchema

router = APIRouter()

@router.get("/record-stopwatch/{task_id}", response_model=Optional[RecordStopwatchSchema], summary="Get Record Stopwatch Info by Task ID")
def get_record_stopwatch_info_api(
    task_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    timer_service = TimerService(db)
    record_info = timer_service.get_record_stopwatch_info(task_id)

    return record_info
