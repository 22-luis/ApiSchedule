import uuid

from sqlalchemy import Column, String, Enum, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.modules.organization.models.role import UserRole
from app.shared.db.database import Base


class UserProfile(Base):
    __tablename__ = 'users_profiles'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)

    full_name = Column(String, nullable=True)
    cargo = Column(String, nullable=True)
    role = Column(Enum(UserRole, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    signature = Column(LargeBinary, nullable=True)

    # Back-reference to the user
    user = relationship("User", back_populates="profile")
