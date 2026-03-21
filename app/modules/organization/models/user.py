import uuid

from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.shared.db.database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    # 1:1 profile with extended fields
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Relationship to UserTeam (Association Object)
    team_associations = relationship("UserTeam", back_populates="user", cascade="all, delete-orphan")

    # Proxy to get teams directly (optional)
    teams = relationship("Team", secondary="user_teams", viewonly=True)

    # ---- Proxy properties for backward compatibility ----

    @property
    def role(self):
        return self.profile.role if self.profile else None

    @role.setter
    def role(self, value):
        if self.profile:
            self.profile.role = value

    @property
    def full_name(self):
        return self.profile.full_name if self.profile else None

    @full_name.setter
    def full_name(self, value):
        if self.profile:
            self.profile.full_name = value

    @property
    def cargo(self):
        return self.profile.cargo if self.profile else None

    @cargo.setter
    def cargo(self, value):
        if self.profile:
            self.profile.cargo = value

    @property
    def signature(self):
        return self.profile.signature if self.profile else None

    @signature.setter
    def signature(self, value):
        if self.profile:
            self.profile.signature = value

    # ---- Team helpers ----

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
