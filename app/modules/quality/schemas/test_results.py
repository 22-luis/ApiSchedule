from uuid import UUID

from pydantic import BaseModel

class TestResultsBase(BaseModel):
    test_record_id: UUID
    catalog_test_id: UUID
    answer: dict

class TestResultsCreate(TestResultsBase):
    pass

class TestResultsUpdate(BaseModel):
    answer: dict | None

class TestResultsOut(TestResultsBase):
    id: UUID