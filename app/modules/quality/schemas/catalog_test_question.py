from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.modules.quality.models.question_type import QuestionType


class CatalogTestQuestionBase(BaseModel):
    catalog_test_id: UUID
    question: str
    specification: str | None = None
    options: str | None = None  # Comma-separated options for closed questions
    type: QuestionType
    chapter_id: UUID | None = None

class CatalogTestQuestionCreate(CatalogTestQuestionBase):
    pass

class CatalogTestQuestionUpdate(BaseModel):
    question: str | None
    specification: str | None
    options: str | None = None
    type: QuestionType | None

class CatalogTestQuestionOut(CatalogTestQuestionBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)