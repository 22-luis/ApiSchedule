from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from app.modules.quality.models.test_status import TestStatus

class TestBase(BaseModel):
    lote: int
    catalog_test_id: UUID
    status: TestStatus = TestStatus.undone
    performed_by: str | None
    performed_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    comment: str | None

class TestCreate(TestBase):
    pass

class TestUpdate(BaseModel):
    status: TestStatus | None
    performed_by: str | None
    performed_at: datetime | None
    approved_by: str | None
    approved_at: datetime | None
    comment: str | None

class TestOut(TestBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
