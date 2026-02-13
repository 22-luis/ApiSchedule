import uuid
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.codes.models.code import Code
    from app.modules.quality.models.catalog_test_question import CatalogTestQuestion

class CodeTestParameterSpecification(Base):
    __tablename__ = "code_test_parameter_specification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("code.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("catalog_test_question.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    specification: Mapped[str] = mapped_column(sa.String, nullable=False)

    # Relationships
    code: Mapped["Code"] = relationship("Code")
    question: Mapped["CatalogTestQuestion"] = relationship("CatalogTestQuestion")
