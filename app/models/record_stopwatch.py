import uuid
from sqlalchemy import Column, Float, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from app.db.database import Base
from sqlalchemy.dialects.postgresql import UUID

class RecordStopwatch(Base):
    __tablename__ = 'record_stopwatch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    quantity = Column(Float, nullable=False)
    accumulated_duration = Column(BigInteger, default=0, nullable=False) # in mili-seconds
    task = relationship('Task', back_populates='record_stopwatch')
