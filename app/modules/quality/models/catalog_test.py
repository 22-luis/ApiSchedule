import uuid
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class CatalogTest(Base):
    __tablename__ = "catalog_test"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    
    # New foreign key relationship to QcManualChapter
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("qc_manual_chapter.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    
    # Legacy field - kept for backward compatibility during migration
    chapter: Mapped[str | None] = mapped_column(String, nullable=True)
    
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    chapter_relation: Mapped[Optional["QcManualChapter"]] = relationship("QcManualChapter", back_populates="catalog_tests")
    questions: Mapped[list["CatalogTestQuestion"]] = relationship("CatalogTestQuestion", back_populates="catalog_test", cascade="all, delete-orphan")


