from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CatalogTestBase(BaseModel):
    name: str
    chapter: str
    status: bool

class CatalogTestCreate(CatalogTestBase):
    pass

class CatalogTestUpdate(BaseModel):
    name: str | None
    chapter: str | None
    status: bool | None

class CatalogTestOut(CatalogTestBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)
