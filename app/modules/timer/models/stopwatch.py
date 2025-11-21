import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, DateTime, ForeignKey, Enum, BigInteger, Boolean
from sqlalchemy.orm import relationship
from app.shared.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from app.modules.timer.models.state import TimerStatus


class Stopwatch(Base):
    __tablename__ = 'stopwatch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    status = Column(Enum(TimerStatus), nullable=False)
    quantity = Column(Float, nullable=False)
    accumulated_duration = Column(Float, default=0, nullable=False) # in hours
    is_from_programming = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=True, default=lambda: datetime.now(timezone.utc))
    update_at = Column(DateTime(timezone=True), nullable=True)
    task = relationship('Task', back_populates='stopwatch')
