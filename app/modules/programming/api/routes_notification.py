from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.modules.core.models.user import User
from app.shared.utils.core.dependencies import require_roles
from app.modules.core.models.role import UserRole
from app.modules.programming.models.task_creation_notification import TaskCreationNotification
from datetime import datetime, timedelta
from typing import List

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
    # Calculate cutoff time (24 hours ago)
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    # Query notifications from the last 24 hours, ordered by newest first
    notifications = db.query(TaskCreationNotification).filter(
        TaskCreationNotification.created_at >= cutoff_time
    ).order_by(
        TaskCreationNotification.created_at.desc()
    ).all()
    
    # Serialize the results
    serialized_notifications = []
    for notification in notifications:
        serialized_notifications.append({
            "id": str(notification.id),
            "created_at": notification.created_at.isoformat(),
            "created_by": notification.created_by,
            "programming_info": notification.programming_info,
            "order_count": notification.order_count
        })
    
    return {
        "notifications": serialized_notifications,
        "total": len(serialized_notifications)
    }
