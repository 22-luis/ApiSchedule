from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.programming.schemas.programming import (
    ProgrammingRead, ProgrammingUpdate, TasksOrderRequest, 
    ProgrammingSummaryResponse, ToggleTaskStatusRequest
)
from app.modules.programming.services import programming_service, task_timer_service
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user, require_roles
from app.shared.utils.business.programming_availability import update_all_programmings_availability_for_date, cleanup_past_programmings

router = APIRouter(prefix="/programmings", tags=["programmings"])

@router.get("/", response_model=List[ProgrammingRead])
def list_programmings(date: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return programming_service.list_programmings(db, current_user, date)

@router.get("/by_team_date", response_model=dict)
def get_programming_by_team_date(team_id: str, date: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return programming_service.get_by_team_date(db, team_id, date, current_user)

@router.get("/summary", response_model=ProgrammingSummaryResponse)
def get_programming_summary(team_id: str, date: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return programming_service.get_summary(db, team_id, date, current_user)

@router.get("/dashboard", response_model=dict)
def get_dashboard_data(date: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return programming_service.get_dashboard_data(db, date, current_user)

@router.put("/{programming_id}/reorder", response_model=dict)
def reorder_tasks_by_programming(
    programming_id: UUID,
    request: TasksOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reorder tasks in a programming. Called by the frontend after drag-and-drop or recalculation."""
    result, error = programming_service.reorder_programming_tasks(db, programming_id, request.tasks_order)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"success": True, "reordered_tasks": result}

@router.post("/start_timer")
def start_timer(task_id: str = Body(..., embed=True), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    success, message = task_timer_service.start_timer(db, task_id, current_user)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.post("/stop_timer")
def stop_timer(task_id: str = Body(..., embed=True), real_quantity: Optional[float] = Body(None, embed=True), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    success, message = task_timer_service.stop_timer(db, task_id, current_user, real_quantity)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.patch("/{programming_id}", response_model=ProgrammingRead)
def update_programming(programming_id: UUID, programming_update: ProgrammingUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))):
    from app.modules.programming.models.programming import Programming
    from app.shared.utils.business.programming_availability import update_programming_availability
    
    db_programming = db.query(Programming).filter(Programming.id == programming_id).first()
    if not db_programming:
        raise HTTPException(status_code=404, detail="Programming not found")
        
    update_data = programming_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_programming, key, value)
        
    db.commit()
    db.refresh(db_programming)
    
    # Actualizar disponibilidad después de cambio de estado
    update_programming_availability(db, db_programming)
    
    return db_programming

@router.post("/cleanup")
def cleanup_programmings(db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN))):
    cleanup_past_programmings(db)
    return {"message": "Past programmings cleaned up"}

@router.post("/refresh_availability")
def refresh_availability(date_str: str = Body(..., embed=True), db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    import datetime
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        update_all_programmings_availability_for_date(db, date_obj)
        return {"message": f"Availability refreshed for {date_str}"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
@router.patch("/{programming_id}/tasks/{task_id}/quantity")
def update_task_real_quantity(
    programming_id: UUID,
    task_id: UUID,
    real_quantity: float = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return programming_service.update_task_real_quantity(db, programming_id, task_id, real_quantity)

@router.post("/{programming_id}/tasks/{task_id}/toggle_status")
def toggle_task_status(
    programming_id: UUID,
    task_id: UUID,
    request: ToggleTaskStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    return programming_service.toggle_task_status(db, programming_id, task_id, request.dict(), current_user)
