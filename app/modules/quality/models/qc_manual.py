import datetime
from datetime import timedelta
import pytz
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.db.database import Base

from app.shared.utils.core.time_utils import TimeZoneUtils

class QcManual(Base):
    __tablename__ = "qc_manual"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, index=True)
    quality_manual_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("quality_manual.id", ondelete="CASCADE"), nullable=False, index=True)
    
    createdAt: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=False), default=TimeZoneUtils.get_now, nullable=False)
    created_by: Mapped[str] = mapped_column(sa.String, nullable=False)
    
    # Relationships
    quality_manual: Mapped["QualityManual"] = relationship("QualityManual", back_populates="revisions")
    chapters: Mapped[list["QcManualChapter"]] = relationship("QcManualChapter", back_populates="manual", cascade="all, delete-orphan")
