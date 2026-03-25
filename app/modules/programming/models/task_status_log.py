import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.shared.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from app.modules.programming.models.state import TaskStatus
from app.shared.utils.core.time_utils import TimeZoneUtils

class TaskStatusLog(Base):
    __tablename__ = 'task_status_log'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False)
    start_time = Column(DateTime(timezone=False), nullable=False, default=TimeZoneUtils.get_now)
    end_time = Column(DateTime(timezone=False), nullable=True)

    task = relationship('Task', back_populates='status_logs')
