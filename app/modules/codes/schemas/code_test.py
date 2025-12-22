from pydantic import BaseModel
from uuid import UUID
from typing import List

class CodeTestLink(BaseModel):
    catalog_test_ids: List[UUID]

class CodeTestOut(BaseModel):
    id: UUID
    code_id: UUID
    catalog_test_id: UUID

    class Config:
        from_attributes = True
