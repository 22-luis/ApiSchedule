import uuid

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Task(Base):
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String)
    description = Column(String)
    unit = Column(String)
    type = Column(String)
    quantity = Column(String)
    minutes = Column(Integer)
    people = Column(Integer)
    performance = Column(Integer)
    material = Column(String)
    presentation = Column(String)
    fabricationCode = Column(String)
    usefulLife = Column(String)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    team = relationship("Team", back_populates="tasks")
