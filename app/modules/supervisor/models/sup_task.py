import uuid

import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.database import Base


class SupTask(Base):
    __tablename__ = "sup_task"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    description: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)