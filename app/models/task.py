import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
from app.models.team import task_team_association
from app.models.code import Code

class Task(Base):
    __tablename__ = 'task'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    code_id = Column(UUID(as_uuid=True), ForeignKey('code.id'), nullable=True)
    code = relationship('Code', backref='tasks')
    lote = Column(String, nullable=True)
    quantity = Column(Integer, nullable=True)
    specification = Column(String, nullable=True)
    preparation_id = Column(UUID(as_uuid=True), ForeignKey('preparation.id'), nullable=True)
    preparation = relationship('Preparation', backref='tasks')
    minutes = Column(Integer, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    teams = relationship('Team', secondary=task_team_association, back_populates='tasks')
    programmings = relationship("Programming", secondary="programming_task", back_populates="tasks")
    
