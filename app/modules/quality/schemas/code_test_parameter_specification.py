from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class CodeTestParameterSpecificationBase(BaseModel):
    code_id: UUID
    question_id: UUID
    specification: str

class CodeTestParameterSpecificationCreate(CodeTestParameterSpecificationBase):
    pass

class CodeTestParameterSpecificationUpdate(BaseModel):
    specification: str

class CodeTestParameterSpecificationOut(CodeTestParameterSpecificationBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class CodeTestParameterSpecificationBatchItem(BaseModel):
    question_id: UUID
    specification: str

class CodeTestParameterSpecificationBatch(BaseModel):
    specifications: List[CodeTestParameterSpecificationBatchItem]
