import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Float, DateTime, ForeignKey, Enum, Boolean
import sqlalchemy as sa
from sqlalchemy.orm import relationship
from app.shared.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from app.modules.timing.models.state import TimerStatus


class SupStopwatch(Base):
    __tablename__ = 'sup_stopwatch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False)
    supervisor_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    status = Column(Enum(TimerStatus), nullable=False)
    accumulated_duration = Column(Float, default=0, nullable=False) # in hours
    real_start_time = Column(DateTime, nullable=True)
    real_end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)

    # Verification fields
    area_limpia = Column(Boolean, default=False, nullable=False)
    peso_verificado = Column(Boolean, default=False, nullable=False)
    selladas = Column(Boolean, default=False, nullable=False)
    contenedores_limpios = Column(Boolean, default=False, nullable=False)
    informacion_correcta = Column(Boolean, default=False, nullable=False)
    etiquetas_correctas = Column(Boolean, default=False, nullable=False)
    contenedores_correctos = Column(Boolean, default=False, nullable=False)
    verificacion_utensilios = Column(Boolean, default=False, nullable=False)
    medidas_tomadas = sa.Column(sa.String, nullable=True) if 'sa' in locals() else Column(sa.String, nullable=True)
    
    task = relationship('Task', backref='sup_stopwatch')
    supervisor = relationship('User', backref='sup_stopwatches')
