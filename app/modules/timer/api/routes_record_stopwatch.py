from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.modules.timer.services.timer import TimerService
import uuid

from typing import Optional
from app.modules.timer.schemas.record_stopwatch import RecordStopwatch as RecordStopwatchSchema, RecordStopwatchComment

router = APIRouter()

@router.get("/record-stopwatch/{task_id}", response_model=Optional[RecordStopwatchSchema], summary="Get Record Stopwatch Info by Task ID")
def get_record_stopwatch_info_api(
    task_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    timer_service = TimerService(db)
    record_info = timer_service.get_record_stopwatch_info(task_id)

    return record_info

@router.post("/record-stopwatch/{record_id}/comment", response_model=RecordStopwatchSchema, summary="Add a comment to a record stopwatch")
def add_comment_to_record_stopwatch(
    record_id: uuid.UUID,
    payload: RecordStopwatchComment,
    db: Session = Depends(get_db)
):
    timer_service = TimerService(db)
    try:
        updated_record = timer_service.add_comment_to_record(record_id, payload.comment)
        return updated_record
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
