from pydantic import BaseModel, ConfigDict
from typing import Any, List
import datetime

class QcManualBase(BaseModel):
    name: str | None = None

class QcManualCreate(QcManualBase):
    content: Any | None = None # Incoming content for processing

class QcManualRename(BaseModel):
    name: str 
    new_name: str

class SectionOut(BaseModel):
    section_name: str
    content: str

class QcManualOut(BaseModel):
    id: int
    quality_manual_id: int
    name: str | None = None
    order: int = 0
    createdAt: datetime.datetime
    created_by: str


    model_config = ConfigDict(from_attributes=True)

class ReorderItem(BaseModel):
    id: str | int
    order: int

class ReorderPayload(BaseModel):
    orders: List[ReorderItem]

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
    order: int = 0
    hierarchy: list[ChapterNode]


# Import for new relational structure
from app.modules.quality.schemas.qc_manual_chapter import QcManualChapterOut


class QcManualWithChaptersOut(BaseModel):
    """Schema for manual output with nested chapters from relational structure"""
    id: int
    quality_manual_id: int
    name: str | None = None
    chapters: List[QcManualChapterOut] = []
    
    model_config = ConfigDict(from_attributes=True)
