import uuid
from sqlalchemy import Column, String, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.modules.codes.models.type import Type
from app.shared.db.database import Base

class CatalogTest(Base):
    __tablename__ = 'catalog_test'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    test = Column(String)
    type = Column(Enum(Type))

