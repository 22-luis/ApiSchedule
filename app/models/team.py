import uuid

from pydantic import BaseModel
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.userTeam import user_team_association
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class Team(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String)
    supervisorId = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    users = relationship("User", secondary=user_team_association, back_populates="teams")