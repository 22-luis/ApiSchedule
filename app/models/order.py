from app.models.state import OrderStatus
from sqlalchemy import Column, String, Enum, Integer, Date
from app.db.database import Base


class Order(Base):
    __tablename__ = "order"
    lote = Column(Integer, primary_key=True, nullable=False)
    description = Column(String)
    quantity = Column(Integer)
    dueDate = Column(Date)
    status = Column(Enum(OrderStatus), default=OrderStatus.unprogrammed)
    code = Column(String)
    bin = Column(Integer)
    received_user = Column(String)
    received_date = Column(Date)
    received_quantity = Column(Integer)
    missing_quantity = Column(Integer)
    submitted_user = Column(String)
    submitted_date = Column(Date)
