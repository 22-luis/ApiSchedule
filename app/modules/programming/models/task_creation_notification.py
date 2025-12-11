import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base


class TaskCreationNotification(Base):
    """
    Model to store notifications about automatic task creation.
    Notifications persist for 24 hours and show which programmings received tasks.
    """
    __tablename__ = "task_creation_notification"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(String, nullable=False)
    
    # JSON field storing list of programming info:
    # [{"team_name": "FABRICADO 1", "programming_date": "2025-12-12", "programming_id": "...", "task_count": 3}, ...]
    programming_info = Column(JSON, nullable=False)
    
    # Total number of orders processed in this batch
    order_count = Column(Integer, nullable=False, default=0)
