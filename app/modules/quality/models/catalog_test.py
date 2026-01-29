import uuid
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

if TYPE_CHECKING:
    from app.modules.quality.models.quality_manual import QualityManual
    from app.modules.quality.models.qc_manual_chapter import QcManualChapter
    from app.modules.quality.models.catalog_test_question import CatalogTestQuestion

class CatalogTest(Base):
    __tablename__ = "catalog_test"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    
    # Relationship to the Manual Identity
    quality_manual_id: Mapped[int | None] = mapped_column(
        sa.Integer, 
        sa.ForeignKey("quality_manual.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )

    # Link to a specific chapter/section
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("qc_manual_chapter.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    
    # Legacy field - kept for backward compatibility during migration
    chapter: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    
    status: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    
    # Relationships
    quality_manual: Mapped[Optional["QualityManual"]] = relationship("QualityManual")
    chapter_relation: Mapped[Optional["QcManualChapter"]] = relationship("QcManualChapter", back_populates="catalog_tests")
    questions: Mapped[list["CatalogTestQuestion"]] = relationship("CatalogTestQuestion", back_populates="catalog_test", cascade="all, delete-orphan")
    @property
    def manual_name(self) -> Optional[str]:
        if self.quality_manual:
            return self.quality_manual.name
        if self.chapter_relation and self.chapter_relation.manual and self.chapter_relation.manual.quality_manual:
            return self.chapter_relation.manual.quality_manual.name
        return None
