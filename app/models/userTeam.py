from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base

user_team_association = Table(
    "user_team_association",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id")),
    Column("team_id", UUID(as_uuid=True), ForeignKey("teams.id")),
)