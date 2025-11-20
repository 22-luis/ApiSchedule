import uuid

from sqlalchemy import Column, String, ForeignKey, Table, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base

# Tabla de asociación para Task y Team
task_team_association = Table(
    "task_team_association",
    Base.metadata,
    Column("task_id", UUID(as_uuid=True), ForeignKey("task.id")),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id")),
)

class UserTeam(Base):
    __tablename__ = 'user_teams'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id'))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="team_associations")
    team = relationship("Team", back_populates="member_associations")

class Team(Base):
    __tablename__ = 'teams'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String)
    supervisorId = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Relationship to UserTeam (Association Object)
    member_associations = relationship("UserTeam", back_populates="team", cascade="all, delete-orphan")
    
    # Proxy to get users directly (optional, but useful for read-only)
    users = relationship("User", secondary="user_teams", viewonly=True)
    
    tasks = relationship('Task', secondary=task_team_association, back_populates='teams')
    programmings = relationship("Programming", back_populates="team")

    @property
    def members(self):
        """
        Returns a list of members formatted for TeamMemberOut schema.
        This bridges the gap between the UserTeam association and the Pydantic schema.
        """
        return [
            {
                "userId": ma.user_id,
                "username": ma.user.username if ma.user else None,
                "startDate": ma.start_date,
                "endDate": ma.end_date
            }
            for ma in self.member_associations
        ]