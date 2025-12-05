from sqlalchemy import Column, DateTime
import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class HistoricoComparacionFechas(Base):
    __tablename__ = "historico_comparacion_fechas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha = Column(DateTime, nullable=False)

