import uuid

from sqlalchemy import Column, String, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.shared.db.database import Base

class Code(Base):
    __tablename__ = 'code'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String, index=True)
    description = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    type = Column(String)
    activity = Column(String)
    quantity = Column(String, nullable=True)
    time = Column(Float, nullable=True)
    people = Column(Integer, nullable=True)
    performance = Column(Float, nullable=True)
    material = Column(String, nullable=True)
    presentation = Column(String, nullable=True)
    fabricationCode = Column(String, nullable=True, index=True)
    usefulLife = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    
    automation_rules = relationship("CodeAutomationRule", back_populates="code", cascade="all, delete-orphan")