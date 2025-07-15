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
    quantity = Column(String)
    minutes = Column(Integer)
    people = Column(Integer)
    performance = Column(Integer)
    material = Column(String)
    presentation = Column(String)
    fabricationCode = Column(String)
    usefulLife = Column(String)
    teams = relationship('Team', secondary=task_team_association, back_populates='tasks')
