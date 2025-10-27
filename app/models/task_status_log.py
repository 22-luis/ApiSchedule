import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
import datetime
from app.models.state import TaskStatus

class TaskStatusLog(Base):
    __tablename__ = 'task_status_log'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False)
    start_time = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    end_time = Column(DateTime(timezone=True), nullable=True)
    task = relationship('Task', back_populates='status_logs')