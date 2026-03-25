import uuid
from datetime import datetime
from sqlalchemy import Column, Float, ForeignKey, BigInteger, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.shared.db.database import Base
from sqlalchemy.dialects.postgresql import UUID

class RecordStopwatch(Base):
    __tablename__ = 'record_stopwatch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    accumulated_duration = Column(Float, default=0, nullable=False) # in hours
    comments = Column(String, nullable=True)
    creation_date = Column(DateTime(timezone=False), default=lambda: datetime.now())
    real_start_time = Column(DateTime(timezone=False), nullable=True)
    real_end_time = Column(DateTime(timezone=False), nullable=True)
    task = relationship('Task', back_populates='record_stopwatch')
