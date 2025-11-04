import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from app.models.state import TaskStatus
from datetime import datetime, timezone

class TaskStatusLog(Base):
    __tablename__ = 'task_status_log'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime(timezone=True), nullable=True)

    task = relationship('Task', back_populates='status_logs')
