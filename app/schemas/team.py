import uuid
from pydantic import BaseModel
from typing import List, Optional
from app.schemas.user import UserOut

class TeamCreate(BaseModel):
    name: str
    supervisorId: uuid.UUID
    userIds: Optional[List[uuid.UUID]] = None

class TeamOut(BaseModel):
    id: uuid.UUID
    name: str
    supervisorId: uuid.UUID
    users: List[UserOut]