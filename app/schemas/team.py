import uuid
from pydantic import BaseModel
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
    supervisorId: uuid.UUID
    members: Optional[List[TeamMemberConfig]] = []

    class Config:
        from_attributes = True

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    supervisorId: Optional[uuid.UUID] = None

class TeamMembersUpdate(BaseModel):
    date: date
    userIds: List[uuid.UUID]

class TeamOut(BaseModel):
    id: uuid.UUID
    name: str
    supervisorId: uuid.UUID
    supervisorUsername: Optional[str] = None
    members: List[TeamMemberOut]

    class Config:
        from_attributes = True