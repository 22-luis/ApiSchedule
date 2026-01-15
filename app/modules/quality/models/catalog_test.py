import uuid

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base

class CatalogTest(Base):
    __tablename__ = "catalog_test"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    chapter: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=True)
    questions: Mapped[list["CatalogTestQuestion"]] = relationship("CatalogTestQuestion", back_populates="catalog_test", cascade="all, delete-orphan")
