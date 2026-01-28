from pydantic import BaseModel, ConfigDict
from typing import Any, List

class QcManualBase(BaseModel):
    name: str | None = None
    content: Any | None = None

class QcManualCreate(QcManualBase):
    pass

class SectionOut(BaseModel):
    section_name: str
    content: str

class QcManualOut(QcManualBase):
    id: int
    version: int


    model_config = ConfigDict(from_attributes=True)

class TestNode(BaseModel):
    id: str | None = None
    title: str
    content: str | None = None

class SubChapterNode(BaseModel):
    id: str | None = None
    title: str
    content: str | None = None
    tests: list[TestNode] = []

class ChapterNode(BaseModel):
    id: str | None = None
    title: str
    content: str | None = None
    sub_chapters: list[SubChapterNode] = []

class Chapters(BaseModel):
    manual_id: int
    chapters: list[str]

class HierarchyOut(BaseModel):
    manual_id: int
    name: str | None = None
    hierarchy: list[ChapterNode]


# Import for new relational structure
from app.modules.quality.schemas.qc_manual_chapter import QcManualChapterOut


class QcManualWithChaptersOut(QcManualBase):
    """Schema for manual output with nested chapters from relational structure"""
    id: int
    version: int
    chapters: List[QcManualChapterOut] = []
    
    model_config = ConfigDict(from_attributes=True)

