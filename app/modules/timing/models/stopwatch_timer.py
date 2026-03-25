import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, DateTime, ForeignKey, Enum, BigInteger, Boolean
from sqlalchemy.orm import relationship
from app.shared.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from app.modules.timing.models.state import TimerStatus


from app.shared.utils.core.time_utils import TimeZoneUtils


class StopwatchTimer(Base):
    __tablename__ = 'stopwatch_timer'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    status = Column(Enum(TimerStatus), nullable=False)
    quantity = Column(Float, nullable=False)
    accumulated_duration = Column(Float, default=0, nullable=False) # in hours
    created_at = Column(DateTime(timezone=False), nullable=True, default=TimeZoneUtils.get_now)
    update_at = Column(DateTime(timezone=False), nullable=True)
    task = relationship('Task', back_populates='stopwatch_timer')
