from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import List

class CodeTestLink(BaseModel):
    catalog_test_ids: List[UUID]

class CodeTestOut(BaseModel):
    id: UUID
    code_id: UUID
    catalog_test_id: UUID

    model_config = ConfigDict(from_attributes=True)
