from pydantic import BaseModel, ConfigDict
from uuid import UUID

from app.modules.codes.models.type import Type

class CatalogTestBase(BaseModel):
    test: str
    type: Type
    options: list[str] | None = None
    manual_section_id: str | None = None

class CatalogTestOut(CatalogTestBase):
    id: UUID
    manual_content: str | None = None

    model_config = ConfigDict(from_attributes=True)

