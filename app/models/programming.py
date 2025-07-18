import uuid

from sqlalchemy import Column, DateTime, UUID, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Programming(Base):
    __tablename__ = 'programming'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    quantity = Column(Integer)
    minutes = Column(Integer)
    date = Column(DateTime)
    task_id = Column(UUID(as_uuid=True), index=True)
    order_lote = Column(Integer, index=True)