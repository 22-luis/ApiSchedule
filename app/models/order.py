import uuid

from app.models.state import OrderStatus
from sqlalchemy import Column, String, Enum, Integer, UUID, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Order(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    description = Column(String)
    quantity = Column(Integer)
    dueDate = Column(DateTime)
    status = Column(Enum(OrderStatus))
    code = Column(String)
    lote = Column(Integer)
    bin = Column(Integer)