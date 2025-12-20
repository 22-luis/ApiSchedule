from sqlalchemy import Column, Integer, JSON
from app.shared.db.database import Base

class QcManual(Base):
    __tablename__ = "qc_manual"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    content = Column(JSON, nullable=False)