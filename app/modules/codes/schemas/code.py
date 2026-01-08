import uuid
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class CodeCreate(BaseModel):
    code: str
    description: Optional[str] = None
    unit: Optional[str] = None
    type: str
    activity: str
    quantity: Optional[str] = None
    time: Optional[float] = None
    people: Optional[int] = None
    performance: Optional[float] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CodeUpdate(BaseModel):
    code: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    activity: Optional[str] = None
    quantity: Optional[str] = None
    time: Optional[float] = None
    people: Optional[int] = None
    performance: Optional[float] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None

class CodeOut(BaseModel):
    id: uuid.UUID
    code: str
    description: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    activity: Optional[str] = None
    quantity: Optional[str] = None
    time: Optional[float] = None
    people: Optional[int] = None
    performance: Optional[float] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CodePageOut(BaseModel):
    codes: List[CodeOut]
    total: int

    model_config = ConfigDict(from_attributes=True)