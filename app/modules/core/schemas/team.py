import uuid
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date

class TeamMemberConfig(BaseModel):
    userId: uuid.UUID
    startDate: date
    endDate: Optional[date] = None

class TeamMemberOut(BaseModel):
    userId: uuid.UUID
    username: Optional[str] = None
    startDate: date
    endDate: Optional[date] = None

class TeamCreate(BaseModel):
    name: str
    supervisorId: Optional[uuid.UUID] = None
    members: Optional[List[TeamMemberConfig]] = []

    model_config = ConfigDict(from_attributes=True)

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    supervisorId: Optional[uuid.UUID] = None

class TeamMembersUpdate(BaseModel):
    date: date
    userIds: List[uuid.UUID]

class TeamOut(BaseModel):
    id: uuid.UUID
    name: str
    supervisorId: Optional[uuid.UUID] = None
    supervisorUsername: Optional[str] = None
    members: List[TeamMemberOut]

    model_config = ConfigDict(from_attributes=True)