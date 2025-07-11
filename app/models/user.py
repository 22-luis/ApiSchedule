import uuid

from pydantic import BaseModel
from sqlalchemy import Column, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.models.role import UserRole
from app.models.state import UserState

class User(BaseModel):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole))
    state = Column(Enum(UserState), default=UserState.ACTIVE)
