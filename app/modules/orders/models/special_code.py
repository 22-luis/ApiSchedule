import uuid
from sqlalchemy import Column, String, Enum, Integer, Date, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class SpecialCode(Base):
    __tablename__ = 'special_codes'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, index=True)
    programming_code = Column(String, nullable=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)