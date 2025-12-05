import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HistoricoComparacionFechasCreate(BaseModel):
    fecha: datetime

class HistoricoComparacionFechasUpdate(BaseModel):
    fecha: Optional[datetime] = None

class HistoricoComparacionFechasOut(BaseModel):
    id: uuid.UUID
    fecha: datetime

    class Config:
        from_attributes = True


