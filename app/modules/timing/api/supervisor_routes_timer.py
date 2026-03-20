import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.organization.models.user import User
from app.modules.timing.services.supervisor_timer_service import SupTimerService
from app.modules.timing.schemas.timer import (
    SupStopwatch as SupStopwatchSchema,
    SupRecordStopwatch as SupRecordStopwatchSchema,
    SupTimerStopPayload,
    SupTaskStatusResponse,
    SupVerificationFields
)
from app.modules.timing.schemas.timer import TaskStatusRequest

router = APIRouter(prefix="/supervisor/timer", tags=["Supervisor Timer"])

@router.post("/start/{task_id}", response_model=SupStopwatchSchema)
def start_supervision(task_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = SupTimerService(db)
    try:
        return service.start_supervision(task_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/pause/{task_id}", response_model=SupStopwatchSchema)
def pause_supervision(task_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = SupTimerService(db)
    try:
        return service.pause_supervision(task_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stop/{task_id}", response_model=SupRecordStopwatchSchema)
def stop_supervision(task_id: uuid.UUID, payload: SupTimerStopPayload, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = SupTimerService(db)
    try:
        # Pass all verification fields
        verification_data = payload.model_dump(exclude={"comments"})
        return service.stop_supervision(task_id, current_user.id, payload.comments, verification_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/update-verification/{task_id}", response_model=SupStopwatchSchema)
def update_verification(
    task_id: uuid.UUID, 
    payload: SupVerificationFields, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    service = SupTimerService(db)
    try:
        return service.update_supervision_data(task_id, current_user.id, payload.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/status", response_model=List[SupTaskStatusResponse])
def get_supervision_status(payload: TaskStatusRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = SupTimerService(db)
    try:
        return service.get_supervision_status(payload.task_ids, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
