from sqlalchemy import Column, String, Numeric, Date,Integer
import uuid
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class Available(Base):
    __tablename__ = "daily_available"

    id=Column(UUID(as_uuid=True), primary_key=True,default=uuid.uuid4)
    codigo = Column(String(20), nullable=True)
    description = Column(String(80), nullable=True)
    disponible= Column(Integer, nullable=True)  
    
    minimo =    Column(Integer, nullable=True)               # tiempo estimado
    reorder =   Column(Integer, nullable=True)   # tiempo real utilizado
    dias_disponibles =   Column(Integer, nullable=True)             # diferencia calculada
    date_upload   = Column(Date, nullable=True) 