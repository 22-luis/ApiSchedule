import uuid

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class CodeVerification(Base):
    __tablename__ = 'code_verification'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    codeId = Column(UUID(as_uuid=True), ForeignKey("code.id"))
    userId = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    minutes = Column(Integer)
    quantity = Column(Float)
    date = Column(DateTime)
    
    code = relationship("Code")
    user = relationship("User")