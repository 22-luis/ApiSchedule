from uuid import UUID

from pydantic import BaseModel

class CodeTestBase(BaseModel):
    code_id: UUID
    catalog_test_id: UUID
