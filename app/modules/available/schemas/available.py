from pydantic import BaseModel, ConfigDict
import uuid
from datetime import date


class AvailableBase(BaseModel):
    codigo: str | None = None
    description: str | None = None
    disponible: int | None = None
    minimo: int | None = None
    reorder: int | None = None
    dias_disponibles: int | None = None
    date_upload: date | None = None


class AvailableCreate(AvailableBase):
    pass


class AvailableUpdate(BaseModel):
    codigo: str | None = None
    description: str | None = None
    disponible: int | None = None
    minimo: int | None = None
    reorder: int | None = None
    dias_disponibles: int | None = None
    date_upload: date | None = None


class AvailableInDBBase(AvailableBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class Available(AvailableInDBBase):
    pass

