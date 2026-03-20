from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Body
from typing import List
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.automation.repositories.automation_repository import AutomationRepository
from app.modules.automation.services.automation_service import AutomationService

router = APIRouter(prefix="/orders/auto", tags=["orders-auto"])

def get_automation_service(db: Session = Depends(get_db)) -> AutomationService:
    return AutomationService(AutomationRepository(db))

@router.post("/trigger")
def trigger_create_tasks(
    lotes: List[int] = Body(..., description="Lista de lotes para crear tareas"),
    background_tasks: BackgroundTasks = None,
    automation_service: AutomationService = Depends(get_automation_service),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    if not lotes:
        raise HTTPException(status_code=400, detail="Se requiere al menos un lote")

    # Schedule background worker
    if background_tasks is not None:
        background_tasks.add_task(automation_service.create_tasks_for_lotes, lotes, current_user.username)
        return {"scheduled": True, "lotes": lotes}
    else:
        # Fallback: run inline
        result = automation_service.create_tasks_for_lotes(lotes, current_user.username)
        return {"scheduled": False, "lotes": lotes, "result": result}
