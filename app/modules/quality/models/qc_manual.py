from datetime import datetime, timedelta
import pytz
from sqlalchemy import Integer, JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.db.database import Base

def get_time():
    tz = pytz.timezone('America/El_Salvador')
    return datetime.now(tz) - timedelta(hours=6)


class QcManual(Base):
    __tablename__ = "qc_manual"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=True) # Added name for multiple manuals
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    
    # Relationships
    chapters: Mapped[list["QcManualChapter"]] = relationship("QcManualChapter", back_populates="manual", cascade="all, delete-orphan")

