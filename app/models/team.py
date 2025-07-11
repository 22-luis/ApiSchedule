import uuid

from pydantic import BaseModel
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

class Team(BaseModel):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String)
    supervisor = Column(UUID(as_uuid=True), ForeignKey("supervisor.id"))