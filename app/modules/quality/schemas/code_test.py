from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import List

class CodeTestBase(BaseModel):
    code_id: UUID
    catalog_test_id: UUID

class CodeTestLink(BaseModel):
    catalog_test_ids: List[UUID]

class CodeTestOut(CodeTestBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
