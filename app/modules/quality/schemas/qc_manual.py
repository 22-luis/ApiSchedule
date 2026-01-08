from pydantic import BaseModel, ConfigDict
from typing import Any

class QcManualBase(BaseModel):
    content: Any | None

class QcManualCreate(QcManualBase):
    pass

class SectionOut(BaseModel):
    section_name: str
    content: str

class QcManualOut(QcManualBase):
    id: int
    version: int

    model_config = ConfigDict(from_attributes=True)
