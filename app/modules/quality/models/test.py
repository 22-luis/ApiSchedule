import uuid
from sqlalchemy import Column, Integer, JSON, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.quality.models.test_status import TestStatus

class Test(Base):
    __tablename__ = 'test'
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lote: Mapped[int] = mapped_column(Integer, ForeignKey("order.lote"), nullable=False)
    status: Mapped[TestStatus] = mapped_column(Enum(TestStatus), default=TestStatus.undone, nullable=False)
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)