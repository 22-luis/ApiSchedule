from pydantic import BaseModel
from uuid import UUID

from app.modules.codes.models.type import Type

class CatalogTestBase(BaseModel):
    test: str
    type: Type
    options: list[str] | None = None
    manual_section_id: str | None = None

class CatalogTestOut(CatalogTestBase):
    id: UUID

