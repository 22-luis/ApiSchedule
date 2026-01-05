import uuid
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class HistoricoComparacionFechasCreate(BaseModel):
    fecha: datetime

class HistoricoComparacionFechasUpdate(BaseModel):
    fecha: Optional[datetime] = None

class HistoricoComparacionFechasOut(BaseModel):
    id: uuid.UUID
    fecha: datetime

    model_config = ConfigDict(from_attributes=True)



