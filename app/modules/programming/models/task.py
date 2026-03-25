import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.shared.db.database import Base
from app.modules.organization.models.team import task_team_association
from app.modules.codes.models.code import Code

class Task(Base):
    __tablename__ = 'task'
    # Identificador único de la tarea
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Referencias y relaciones principales
    code_id = Column(UUID(as_uuid=True), ForeignKey('code.id'), nullable=True)
    code = relationship('Code', backref='tasks')
    preparation_id = Column(UUID(as_uuid=True), ForeignKey('preparation.id'), nullable=True)
    preparation = relationship('Preparation', backref='tasks')
    teams = relationship('Team', secondary=task_team_association, back_populates='tasks')
    programmings = relationship("Programming", secondary="programming_task", viewonly=True)
    programming_tasks = relationship("ProgrammingTask", back_populates="task", cascade="all, delete-orphan")
    # Campo para rastrear quién creó la tarea
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_by_user = relationship('User', foreign_keys=[created_by_user_id])
    # Información principal de la tarea
    lote = Column(String, nullable=True, index=True)
    # Campo para almacenar el lote original de empaque cuando se usa el lote de fabricación
    original_packaging_lote = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    specification = Column(String, nullable=True)
    minutes = Column(Integer, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    people = Column(Integer, nullable=True)
    performance = Column(Float, nullable=True)
    material = Column(String, nullable=True)
    presentation = Column(String, nullable=True)
    fabricationCode = Column(String, nullable=True, index=True)
    usefulLife = Column(String, nullable=True)
    related_task_code = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    type = Column(String, nullable=True, index=True)
    activity = Column(String, nullable=True, index=True)
    description = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pendiente', index=True)
    is_completed = Column(Boolean, default=False, nullable=False)

    status_logs = relationship('TaskStatusLog', back_populates='task', cascade='all, delete-orphan')
    record_stopwatch = relationship('RecordStopwatch', back_populates='task', cascade='all, delete-orphan')
    stopwatch = relationship('Stopwatch', back_populates='task', cascade='all, delete-orphan')