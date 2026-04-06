import uuid

from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.shared.db.database import Base

class CodeAutomationRule(Base):
    __tablename__ = 'code_automation_rules'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    code_id = Column(UUID(as_uuid=True), ForeignKey('code.id'), nullable=False)
    
    service_type = Column(String, nullable=False)  # e.g., 'FABRICATION', 'PACKAGING', 'WEIGHING'
    activity_type = Column(String, nullable=True)  # e.g., 'M1', 'M5' (Nullable means any)
    priority = Column(Integer, nullable=False, default=1)
    
    min_quantity = Column(Float, nullable=True)
    max_quantity = Column(Float, nullable=True)
    
    target_team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id'), nullable=False)
    overflow_team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id'), nullable=True)

    # Relaciones
    code = relationship("Code", back_populates="automation_rules")
    target_team = relationship("Team", foreign_keys=[target_team_id])
    overflow_team = relationship("Team", foreign_keys=[overflow_team_id])
