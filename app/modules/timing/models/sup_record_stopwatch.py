import uuid
from sqlalchemy import Column, Float, ForeignKey, DateTime, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.shared.db.database import Base
from sqlalchemy.dialects.postgresql import UUID
from app.shared.utils.core.time_utils import TimeZoneUtils

class SupRecordStopwatch(Base):
    __tablename__ = 'sup_record_stopwatch'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey('task.id'), nullable=False, index=True)
    supervisor_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    accumulated_duration = Column(Float, default=0, nullable=False) # in hours
    comments = Column(String, nullable=True)
    medidas_tomadas = Column(String, nullable=True)
    creation_date = Column(DateTime(timezone=False), default=TimeZoneUtils.get_now)
    real_start_time = Column(DateTime(timezone=False), nullable=True)
    real_end_time = Column(DateTime(timezone=False), nullable=True)
    
    # Verification fields
    area_limpia = Column(Boolean, default=False, nullable=False)
    peso_verificado = Column(Boolean, default=False, nullable=False)
    selladas = Column(Boolean, default=False, nullable=False)
    contenedores_limpios = Column(Boolean, default=False, nullable=False)
    informacion_correcta = Column(Boolean, default=False, nullable=False)
    etiquetas_correctas = Column(Boolean, default=False, nullable=False)
    contenedores_correctos = Column(Boolean, default=False, nullable=False)
    verificacion_utensilios = Column(Boolean, default=False, nullable=False)
    
    task = relationship('Task', backref='sup_record_stopwatch')
    supervisor = relationship('User', backref='sup_records')
