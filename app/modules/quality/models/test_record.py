import uuid
from datetime import datetime
from typing import List
from sqlalchemy import Integer, ForeignKey, Enum, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.quality.models.test_status import TestStatus

class TestRecord(Base):
    __tablename__ = 'test_record'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lote: Mapped[int] = mapped_column(Integer, ForeignKey("order.lote"), nullable=False)
    code_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("code.id"), nullable=False)
    status: Mapped[TestStatus] = mapped_column(Enum(TestStatus), default=TestStatus.undone, nullable=False)
    performed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comment: Mapped[str | None] = mapped_column(String, nullable=True)
    analysis_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    results: Mapped[List["TestResults"]] = relationship("TestResults", back_populates="test_record", cascade="all, delete-orphan")