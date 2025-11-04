import uuid
from sqlalchemy import Column, Float, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID

class RecordStopwatch(Base):
    __tablename__ = 'record_stopwatch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    accumulated_duration = Column(Float, default=0, nullable=False) # in hours
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    task = relationship('Task', back_populates='record_stopwatch')
