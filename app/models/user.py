import uuid

from sqlalchemy import Column, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.role import UserRole
from app.models.state import UserState
from app.models.team import user_team_association
from app.db.database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole))
    state = Column(Enum(UserState), default=UserState.ACTIVE)
    teams = relationship("Team", secondary=user_team_association, back_populates="users")
