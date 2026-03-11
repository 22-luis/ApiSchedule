from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Body
from typing import List
from app.shared.utils.core.dependencies import require_roles
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.automation.services.auto import create_tasks_for_lotes

router = APIRouter(prefix="/orders/auto", tags=["orders-auto"])


@router.post("/trigger")
def trigger_create_tasks(
    lotes: List[int] = Body(..., description="Lista de lotes para crear tareas"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    if not lotes:
        raise HTTPException(status_code=400, detail="Se requiere al menos un lote")

    # Schedule background worker
    if background_tasks is not None:
        background_tasks.add_task(create_tasks_for_lotes, lotes, current_user.username)
        return {"scheduled": True, "lotes": lotes}
    else:
        # Fallback: run inline
        create_tasks_for_lotes(lotes, current_user.username)
        return {"scheduled": False, "lotes": lotes}
