import uuid
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.quality.models.question_type import QuestionType

if TYPE_CHECKING:
    from app.modules.quality.models.catalog_test import CatalogTest
    from app.modules.quality.models.qc_manual_chapter import QcManualChapter

class CatalogTestQuestion(Base):
    __tablename__ = "catalog_test_question"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("catalog_test.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("qc_manual_chapter.id", ondelete="SET NULL"), 
        nullable=True,
        index=True
    )
    
    question: Mapped[str] = mapped_column(sa.String, nullable=False)
    specification: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    type: Mapped[QuestionType] = mapped_column(sa.Enum(QuestionType), nullable=False)
    
    catalog_test: Mapped["CatalogTest"] = relationship("CatalogTest", back_populates="questions")
    chapter_relation: Mapped[Optional["QcManualChapter"]] = relationship("QcManualChapter")
