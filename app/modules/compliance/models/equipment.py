import uuid

from sqlalchemy import Column
from app.shared.db.database import Base
from sqlalchemy.dialects.postgresql import UUID

class Equipment(Base):
    __tablename__ = 'equipment'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    code = Column(String(255), nullable=False)
    
