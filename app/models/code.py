"""
Modelo que representa un código predefinido para tareas o productos, con sus atributos y relaciones.
"""
import uuid

from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

class Code(Base):
    __tablename__ = 'code'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String)
    description = Column(String)
    unit = Column(String)
    type = Column(String)
    activity = Column(String)
    quantity = Column(String, nullable=True)
    time = Column(Float, nullable=True)
    people = Column(Integer, nullable=True)
    performance = Column(Float, nullable=True)
    material = Column(String)
    presentation = Column(String)
    fabricationCode = Column(String, nullable=True)
    usefulLife = Column(String)