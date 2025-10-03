import uuid

from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class Code(Base):
    __tablename__ = 'code'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String)
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
    fabricationCode = Column(String, nullable=True)
    usefulLife = Column(String, nullable=True)