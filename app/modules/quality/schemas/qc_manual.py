from pydantic import BaseModel
from typing import Any, Optional

class QcManualBase(BaseModel):
    content: Optional[Any] = None

class QcManualCreate(QcManualBase):
    pass

class QcManualOut(QcManualBase):
    id: int
    version: int

    class Config:
        from_attributes = True
