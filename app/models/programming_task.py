import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base

class ProgrammingTask(Base):
    __tablename__ = "programming_task"
    programming_id = Column(UUID(as_uuid=True), ForeignKey("programming.id"), primary_key=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("task.id"), primary_key=True)
    order = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    programming = relationship("Programming", back_populates="programming_tasks")
    task = relationship("Task", back_populates="programming_tasks") 