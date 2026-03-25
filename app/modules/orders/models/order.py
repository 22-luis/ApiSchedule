from sqlalchemy import Column, String, Enum, Integer, Date, Float, Boolean, DateTime
from app.shared.db.database import Base
from app.modules.orders.models.state import OrderStatus

class Order(Base):
    __tablename__ = "order"
    lote = Column(Integer, primary_key=True, nullable=False)
    description = Column(String)
    quantity = Column(Float)
    dueDate = Column(Date)
    status = Column(Enum(OrderStatus), default=OrderStatus.unprogrammed, index=True)
    code = Column(String, index=True)
    bin = Column(Integer)
    received_user = Column(String)
    received_date = Column(Date)
    received_quantity = Column(Float)
    fabricated_quantity = Column(Float, nullable=True)
    missing_quantity = Column(Float)
    submitted_user = Column(String)
    submitted_date = Column(Date)
    submitted_observations = Column(String)
    is_hidden = Column(Boolean, default=False, nullable=True)
    hidden_at = Column(DateTime, nullable=True)
