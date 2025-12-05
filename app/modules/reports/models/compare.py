from sqlalchemy import Column, String, Numeric, Date
import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class ProductionReport(Base):
    __tablename__ = "history_comparison"

    id=Column(UUID(as_uuid=True), primary_key=True,default=uuid.uuid4)
    code = Column(String(20), nullable=True)
    description = Column(String(50), nullable=True)
    tipo = Column(String(20), nullable=True)
    
    tiempo = Column(Numeric(7, 3), nullable=True)               # tiempo estimado
    total_tiempo_real = Column(Numeric(7, 3), nullable=True)    # tiempo real utilizado
    diferencia = Column(Numeric(6, 2), nullable=True)           # diferencia calculada
    compare_date = Column(Date, nullable=True)                  # fecha a comparar
