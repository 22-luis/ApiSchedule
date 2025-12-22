from pydantic import BaseModel
from uuid import UUID

from app.modules.codes.models.type import Type

class CatalogTestBase(BaseModel):
    test: str
    type: Type

class CatalogTestOut(CatalogTestBase):
    id: UUID

