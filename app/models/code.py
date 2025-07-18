import uuid

from sqlalchemy import Column, String, Integer, ForeignKey, Table, Float
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

code_team_association = Table(
    'code_team_association',
    Base.metadata,
    Column('code_id', UUID(as_uuid=True), ForeignKey('code.id')),
    Column('team_id', UUID(as_uuid=True), ForeignKey('teams.id'))
)

class Code(Base):
    __tablename__ = 'code'
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    code = Column(String)
    description = Column(String)
    unit = Column(String)
    type = Column(String)
    activity = Column(String)
    quantity = Column(String, nullable=True)
    time = Column(Float, nullable=True)
    people = Column(Integer, nullable=True)
    performance = Column(Integer, nullable=True)
    material = Column(String)
    presentation = Column(String)
    fabricationCode = Column(String, nullable=True)
    usefulLife = Column(String)
    related_code_team = Column(String, nullable=True)
    teams = relationship('Team', secondary=code_team_association, back_populates='codes')