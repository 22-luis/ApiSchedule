import uuid

from sqlalchemy import ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.database import Base

class TestResults(Base):
    __tablename__ = "test_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_record.id"), nullable=False)
    catalog_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("catalog_test.id", ondelete="CASCADE"), 
        nullable=False
    )
    answer: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Relationships
    test_record: Mapped["TestRecord"] = relationship("TestRecord", back_populates="results")
    catalog_test: Mapped["CatalogTest"] = relationship("CatalogTest", back_populates="results")

