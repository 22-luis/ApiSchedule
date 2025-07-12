import uuid
from pydantic import BaseModel
from app.models.role import UserRole
from app.models.state import UserState
from app.models.team import Team
from typing import List, Optional

class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole
    state: UserState
    teamIds: Optional[List[uuid.UUID]]

class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole
    state: UserState = UserState.ACTIVE
    teamIds: Optional[List[uuid.UUID]] = []
