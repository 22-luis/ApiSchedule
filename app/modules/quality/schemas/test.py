from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from app.modules.quality.models.test_status import TestStatus

class TestBase(BaseModel):
    lote: int
    status: Optional[TestStatus] = TestStatus.undone
    performed_by: Optional[str] = None
    performed_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None

class TestCreate(TestBase):
    pass

class TestUpdate(BaseModel):
    status: Optional[TestStatus] = None
    performed_by: Optional[str] = None
    performed_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    results: Optional[Dict[str, Any]] = None

class TestOut(TestBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
