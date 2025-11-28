import uuid

from sqlalchemy import Column, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.modules.core.models.role import UserRole
from app.modules.core.models.state import UserState
from app.shared.db.database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole))
    state = Column(Enum(UserState), default=UserState.ACTIVE)
    # Relationship to UserTeam (Association Object)
    team_associations = relationship("UserTeam", back_populates="user", cascade="all, delete-orphan")
    
    # Proxy to get teams directly (optional)
    teams = relationship("Team", secondary="user_teams", viewonly=True)
