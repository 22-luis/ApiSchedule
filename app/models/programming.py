import uuid

from sqlalchemy import Column, DateTime, UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Programming(Base):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    