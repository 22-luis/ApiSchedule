import uuid

from sqlalchemy import ForeignKey, String, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.quality.models.question_type import QuestionType

class CatalogTestQuestion(Base):
    __tablename__ = "catalog_test_question"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("catalog_test.id"), nullable=False)
    question: Mapped[str] = mapped_column(String, nullable=False)
    specification: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)