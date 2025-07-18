from sqlalchemy import Column, DateTime, Integer, ForeignKey, String, Date, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

class ProgrammingTask(Base):
    __tablename__ = "programming_task"
    programming_id = Column(UUID(as_uuid=True), ForeignKey("programming.id"), primary_key=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("task.id"), primary_key=True)
    order = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    programming = relationship("Programming", back_populates="programming_tasks")
    task = relationship("Task", back_populates="programming_tasks")

class Programming(Base):
    __tablename__ = "programming"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(Date, nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    team = relationship("Team", back_populates="programmings")
    programming_tasks = relationship("ProgrammingTask", back_populates="programming", cascade="all, delete-orphan")
    tasks = relationship("Task", secondary="programming_task", viewonly=True)
    __table_args__ = (UniqueConstraint('date', 'team_id', name='_date_team_uc'),)