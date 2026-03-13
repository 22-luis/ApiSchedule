from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.modules.organization.models.user import User
from app.shared.utils.core.dependencies import require_roles
from app.modules.organization.models.role import UserRole
from app.modules.programming.services.programming_service import ProgrammingService

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.get("/task-creation/recent")
def get_recent_task_creation_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Retrieve task creation notifications from the last 24 hours.
    Shows which programmings received automatic tasks when orders were created.
    """
    notifications = ProgrammingService.get_recent_task_creation_notifications(db)
    return {
        "notifications": notifications,
        "total": len(notifications)
    }
