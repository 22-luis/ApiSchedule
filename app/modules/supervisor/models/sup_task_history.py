import uuid
from datetime import datetime

import sqlalchemy
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.database import Base


class SupTaskHistory(Base):
    __tablename__ = "sup_task_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sup_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sup_task.id"), nullable=False)
    status: Mapped[bool] = mapped_column(sqlalchemy.Boolean, nullable=False)
    observation: Mapped[str] = mapped_column(sqlalchemy.String, nullable=True)
    date: Mapped[datetime] = mapped_column(sqlalchemy.DateTime, nullable=False)