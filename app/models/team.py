import uuid

from sqlalchemy import Column, String, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.models.code import code_team_association

# Tabla de asociación para Task y Team

user_team_association = Table(
    "user_team_association",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id")),
)

task_team_association = Table(
    "task_team_association",
    Base.metadata,
    Column("task_id", UUID(as_uuid=True), ForeignKey("task.id")),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id")),
)

class Team(Base):
    __tablename__ = 'teams'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String)
    supervisorId = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    users = relationship("User", secondary=user_team_association, back_populates="teams")
    tasks = relationship('Task', secondary=task_team_association, back_populates='teams')
    codes = relationship('Code', secondary=code_team_association, back_populates='teams')
    programmings = relationship("Programming", back_populates="team")