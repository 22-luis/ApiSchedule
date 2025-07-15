import uuid

from app.models.state import OrderStatus
from sqlalchemy import Column, String, Enum, Integer, UUID, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Order(Base):
    __tablename__ = 'order'
    lote = Column(Integer, primary_key=True, nullable=False)
    description = Column(String)
    quantity = Column(Integer)
    dueDate = Column(DateTime)
    status = Column(Enum(OrderStatus))
    code = Column(String)
    bin = Column(Integer)