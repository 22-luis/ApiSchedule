from uuid import UUID


from pydantic import BaseModel

from app.modules.quality.models.question_type import QuestionType


class CatalogTestQuestionBase(BaseModel):
    catalog_test_id: UUID
    question: str
    specification: str | None
    type: QuestionType

class CatalogTestQuestionCreate(CatalogTestQuestionBase):
    pass

class CatalogTestQuestionUpdate(BaseModel):
    question: str | None
    specification: str | None
    type: QuestionType | None

class CatalogTestQuestionOut(CatalogTestQuestionBase):
    id: UUID