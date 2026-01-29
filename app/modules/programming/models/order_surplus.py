import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class OrderSurplus(Base):
    __tablename__ = "order_surplus"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lote = Column(Integer, ForeignKey("order.lote"), nullable=False)
    date = Column(Date, nullable=False, default=datetime.now().date())
    code = Column(String, nullable=False)
    description = Column(String, nullable=True)
    original_quantity = Column(Float, nullable=False)
    received_quantity = Column(Float, nullable=False)
    surplus = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
