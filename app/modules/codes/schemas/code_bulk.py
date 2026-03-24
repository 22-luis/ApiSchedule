import uuid
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict

class CodeBulkItem(BaseModel):
    id: Optional[uuid.UUID] = None
    code: str
    activity: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    quantity: Optional[Any] = None
    time: Optional[Any] = None
    people: Optional[Any] = None
    performance: Optional[Any] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None

    model_config = ConfigDict(extra='allow') # Permitir columnas extra que puedan venir del Excel
