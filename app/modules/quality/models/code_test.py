import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.database import Base


class CodeTest(Base):
    __tablename__ = 'code_test'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('code.id'), nullable=False)
    catalog_test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey('catalog_test.id', ondelete="CASCADE"), 
        nullable=False
    )

    catalog_test: Mapped["CatalogTest"] = relationship("CatalogTest", back_populates="code_associations")