import enum
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, ForeignKey, String, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.shared.db.database import Base

class WarehouseHistoryType(str, enum.Enum):
    SENT = "SENT"
    RECEIVED = "RECEIVED"
    TRANSFER_SOURCE = "TRANSFER_SOURCE"
    TRANSFER_TARGET = "TRANSFER_TARGET"

class WarehouseHistory(Base):
    __tablename__ = "warehouse_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lote = Column(Integer, ForeignKey("order.lote"), nullable=False)
    code = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    type = Column(Enum(WarehouseHistoryType), nullable=False)
    user = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    observations = Column(String, nullable=True)
