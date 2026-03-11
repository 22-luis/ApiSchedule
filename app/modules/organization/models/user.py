import uuid

from sqlalchemy import Column, String, Enum, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.state import UserState
from app.shared.db.database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    cargo = Column(String, nullable=True)
    role = Column(Enum(UserRole, values_callable=lambda obj: [e.value for e in obj]))
    state = Column(Enum(UserState), default=UserState.ACTIVE)
    signature = Column(LargeBinary, nullable=True)
    document_name = Column(String, nullable=True)
    # Relationship to UserTeam (Association Object)
    team_associations = relationship("UserTeam", back_populates="user", cascade="all, delete-orphan")
    
    # Proxy to get teams directly (optional)
    teams = relationship("Team", secondary="user_teams", viewonly=True)

    @property
    def active_team_ids(self):
        """Returns IDs of teams where the user is currently active based on start_date and end_date."""
        from datetime import date
        today = date.today()
        return [
            assoc.team_id 
            for assoc in self.team_associations 
            if assoc.start_date <= today and (assoc.end_date is None or assoc.end_date >= today)
        ]

    @property
    def teamIds(self):
        """Alias for active_team_ids to match Pydantic schema naming."""
        return self.active_team_ids
