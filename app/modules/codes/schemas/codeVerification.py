import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Optional

class CodeVerificationSchema(BaseModel):
    codeId: uuid.UUID
    userId: uuid.UUID
    minutes: int
    quantity: Optional[float] = None
    date: datetime

    model_config = ConfigDict(from_attributes=True)

class CodeVerificationOut(CodeVerificationSchema):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)