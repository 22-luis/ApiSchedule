from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from app.modules.quality.models.test_status import TestStatus

class TestBase(BaseModel):
    lote: int
    status: Optional[TestStatus] = TestStatus.undone
    results: Optional[Dict[str, Any]] = None

class TestCreate(TestBase):
    pass

class TestOut(TestBase):
    id: UUID

    class Config:
        from_attributes = True
