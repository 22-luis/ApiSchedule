from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, ForeignKey, String, Date, UniqueConstraint, Boolean, Enum, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.modules.programming.models.state import ProgrammingStatus
from app.shared.db.database import Base

class ProgrammingTask(Base):
    __tablename__ = "programming_task"
    programming_id = Column(UUID(as_uuid=True), ForeignKey("programming.id"), primary_key=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("task.id"), primary_key=True)
    created_at = Column('created_at',DateTime, default=datetime.now())
    order = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    real_start_time = Column(DateTime, nullable=True)
    real_end_time = Column(DateTime, nullable=True)
    real_quantity = Column(Float, nullable=True)
    duration_in_hours = Column(Float, nullable=True)
    comment = Column(String, nullable=True)
    completed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_completed = Column(Boolean, nullable=True, default=None)
    programming = relationship("Programming", back_populates="programming_tasks")
    task = relationship("Task", back_populates="programming_tasks")

class Programming(Base):
    __tablename__ = "programming"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False)
    status = Column(Enum(ProgrammingStatus), nullable=False, default=ProgrammingStatus.available)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    team = relationship("Team", back_populates="programmings")
    programming_tasks = relationship("ProgrammingTask", back_populates="programming", cascade="all, delete-orphan")
    tasks = relationship("Task", secondary="programming_task", viewonly=True)
    __table_args__ = (UniqueConstraint('date', 'team_id', name='_date_team_uc'),)