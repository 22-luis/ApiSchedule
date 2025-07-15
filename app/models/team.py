import uuid

from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.task import task_team_association

user_team_association = Table(
    "user_team_association",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id")),
)

class Team(Base):
    __tablename__ = 'teams'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String)
    supervisorId = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    users = relationship("User", secondary=user_team_association, back_populates="teams")
    tasks = relationship('Task', secondary=task_team_association, back_populates='teams')