import uuid

from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class Preparation(Base):
    __tablename__ = 'preparation'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    description = Column(String)
    minutes = Column(Integer)