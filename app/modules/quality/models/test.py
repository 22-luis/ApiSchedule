import uuid
from sqlalchemy import Column, Integer, JSON, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.quality.models.test_status import TestStatus

class Test(Base):
    __tablename__ = 'test'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lote = Column(Integer, ForeignKey('order.lote'), nullable=False)
    status = Column(Enum(TestStatus), default=TestStatus.undone, nullable=False)
    results = Column(JSON, nullable=True)