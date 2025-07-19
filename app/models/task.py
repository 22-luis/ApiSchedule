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
    programmings = relationship("Programming", secondary="programming_task", viewonly=True)
    programming_tasks = relationship("ProgrammingTask", back_populates="task", cascade="all, delete-orphan")
    people = Column(Integer, nullable=True)
    performance = Column(Integer, nullable=True)
    material = Column(String, nullable=True)
    presentation = Column(String, nullable=True)
    fabricationCode = Column(String, nullable=True)
    usefulLife = Column(String, nullable=True)
    related_task_code = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    type = Column(String, nullable=True)
    activity = Column(String, nullable=True)
    description = Column(String, nullable=True)