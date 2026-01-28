import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.quality.models.qc_manual import get_time


class QcManualChapter(Base):
    __tablename__ = "qc_manual_chapter"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manual_id: Mapped[int] = mapped_column(Integer, ForeignKey("qc_manual.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("qc_manual_chapter.id", ondelete="CASCADE"), 
        nullable=True,
        index=True
    )
    
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # HTML content
    chapter_type: Mapped[str] = mapped_column(String, nullable=False)  # 'chapter', 'sub_chapter', 'test'
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # Display order within parent
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=get_time, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    
    # Relationships
    manual: Mapped["QcManual"] = relationship("QcManual", back_populates="chapters")
    parent_chapter: Mapped[Optional["QcManualChapter"]] = relationship(
        "QcManualChapter", 
        remote_side=[id], 
        back_populates="sub_chapters",
        foreign_keys=[parent_chapter_id]
    )
    sub_chapters: Mapped[List["QcManualChapter"]] = relationship(
        "QcManualChapter", 
        back_populates="parent_chapter",
        foreign_keys=[parent_chapter_id],
        cascade="all, delete-orphan"
    )
    catalog_tests: Mapped[List["CatalogTest"]] = relationship("CatalogTest", back_populates="chapter_relation")
