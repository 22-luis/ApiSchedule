import uuid
from sqlalchemy import Column, String, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.codes.models.type import Type

class CatalogTest(Base):
    __tablename__ = 'catalog_test'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test = Column(String, nullable=False)
    type = Column(Enum(Type), nullable=False)
    options = Column(JSON, nullable=True)
