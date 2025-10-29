import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean
from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID

class RecordStopwatch(Base):
    __tablename__ = 'record_stopwatch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lote = Column(String, nullable=True)
    code = Column(String, nullable=False)
    description = Column(String, nullable=True)
    people = Column(Integer, nullable=True)
    quantity = Column(Float, nullable=False)
    real_quantity = Column(Float, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    accumulated_duration = Column(Integer, default=0, nullable=False) # in seconds
    is_paused = Column(Boolean, default=False, nullable=False)
