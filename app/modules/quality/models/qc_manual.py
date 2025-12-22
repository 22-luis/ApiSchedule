from datetime import datetime
import pytz
from sqlalchemy import Column, Integer, JSON, DateTime
from app.shared.db.database import Base

def get_time():
    tz = pytz.timezone('America/El_Salvador')
    return datetime.now(tz)


class QcManual(Base):
    __tablename__ = "qc_manual"
    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    createdAt = Column(DateTime(timezone=True), default=get_time(), nullable=False)