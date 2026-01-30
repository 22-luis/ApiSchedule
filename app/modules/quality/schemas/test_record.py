from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from app.modules.quality.models.test_status import TestStatus

from typing import List
from app.modules.quality.schemas.test_results import TestResultsOut, TestResultsCreate

class TestBase(BaseModel):
    lote: int
    code_id: UUID
    status: TestStatus = TestStatus.undone
    performed_by: str | None = None
    performed_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    comment: str | None = None

class TestCreate(TestBase):
    pass

class TestSessionCreate(BaseModel):
    lote: int
    code_id: UUID
    results: List[TestResultsCreate]
    comment: str | None = None

class TestUpdate(BaseModel):
    status: TestStatus | None = None
    performed_by: str | None = None
    performed_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    comment: str | None = None

class TestOut(TestBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)

class TestSessionOut(TestOut):
    results: List[TestResultsOut] = []
