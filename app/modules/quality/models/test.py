import uuid

from sqlalchemy import Column, UUID, Enum, JSON

from app.modules.quality.models.test_status import TestStatus
from app.shared.db.database import Base


class Test(Base):
    __tablename__ = 'test'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    status = Column(Enum(TestStatus))
    results = Column(JSON)