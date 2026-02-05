from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.db.database import Base
from app.modules.quality.models.qc_manual import get_time

class QualityManual(Base):
    __tablename__ = "quality_manual"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)

    # Relationships
    revisions: Mapped[list["QcManual"]] = relationship("QcManual", back_populates="quality_manual", cascade="all, delete-orphan")
