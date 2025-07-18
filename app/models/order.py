import uuid

from app.models.state import OrderStatus
from sqlalchemy import Column, String, Enum, Integer, UUID, Date
from app.db.database import Base

class Order(Base):
    __tablename__ = 'order'
    lote = Column(Integer, primary_key=True, nullable=False)
    description = Column(String)
    quantity = Column(Integer)
    dueDate = Column(Date)
    status = Column(Enum(OrderStatus))
    code = Column(String)
    bin = Column(Integer)