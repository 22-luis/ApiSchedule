from sqlalchemy import Column, Integer, JSON, DateTime
from sqlalchemy.sql import func
from app.shared.db.database import Base

class QcManual(Base):
    __tablename__ = "qc_manual"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    createdAt = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)