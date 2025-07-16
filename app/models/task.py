import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

task_team_association = Table(
    'task_team_association',
    Base.metadata,
    Column('task_id', UUID(as_uuid=True), ForeignKey('task.id')),
    Column('team_id', UUID(as_uuid=True), ForeignKey('teams.id'))
)

class Task(Base):
    __tablename__ = 'task'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String)
    description = Column(String)
    unit = Column(String)
    type = Column(String)
    activity = Column(String)
    quantity = Column(String, nullable=True)
    minutes = Column(Integer, nullable=True)
    performance = Column(Integer, nullable=True)
    material = Column(String)
    presentation = Column(String)
    fabricationCode = Column(String, nullable=True)
    usefulLife = Column(String)
    parent_id = Column(UUID, ForeignKey('task.id'), nullable=True)
    parent = relationship('Task', remote_side='Task.id', backref='subtasks')
    teams = relationship('Team', secondary=task_team_association, back_populates='tasks')
