from uuid import UUID

from pydantic import BaseModel

class TestResultsBase(BaseModel):
    test_record_id: UUID | None = None
    catalog_test_id: UUID
    answer: dict

class TestResultsCreate(BaseModel):
    catalog_test_id: UUID
    answer: dict

class TestResultsUpdate(BaseModel):
    answer: dict | None

class TestResultsOut(TestResultsBase):
    id: UUID