from uuid import UUID

from pydantic import BaseModel, ConfigDict
from app.modules.quality.schemas.catalog_test_question import CatalogTestQuestionOut, QuestionType


class CatalogTestBase(BaseModel):
    name: str
    chapter: str
    chapter_id: UUID | None = None
    quality_manual_id: int | None = None
    status: bool

class CatalogTestQuestionNested(BaseModel):
    question: str
    specification: str | None = None
    options: str | None = None  # Comma-separated options for closed questions
    type: QuestionType
    chapter_id: UUID | None = None

class CatalogTestCreate(CatalogTestBase):
    questions: list[CatalogTestQuestionNested] | None = None

class CatalogTestUpdate(BaseModel):
    name: str | None = None
    chapter: str | None = None
    chapter_id: UUID | None = None
    quality_manual_id: int | None = None
    status: bool | None = None
    questions: list[CatalogTestQuestionNested] | None = None

class CatalogTestOut(CatalogTestBase):
    id: UUID
    manual_name: str | None = None
    instructions: str | None = None
    questions: list[CatalogTestQuestionOut] = []

    model_config = ConfigDict(from_attributes=True)
