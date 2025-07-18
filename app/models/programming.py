from sqlalchemy import Column, DateTime, UUID, Integer, String, Date, ForeignKey, Table, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
import uuid

programming_task = Table(
    "programming_task",
    Base.metadata,
    Column("programming_id", Integer, ForeignKey("programming.id")),
    Column("task_id", UUID(as_uuid=True), ForeignKey("task.id"))
)

class Programming(Base):
    __tablename__ = "programming"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    date = Column(Date, nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    team = relationship("Team", back_populates="programmings")
    tasks = relationship("Task", secondary=programming_task, back_populates="programmings")

    __table_args__ = (UniqueConstraint('date', 'team_id', name='_date_team_uc'),)