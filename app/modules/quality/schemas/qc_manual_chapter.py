import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


class QcManualChapterBase(BaseModel):
    """Base schema for QcManualChapter"""
    title: str = Field(..., description="Chapter title")
    content: Optional[Any] = Field(None, description="HTML content or JSON structure of the chapter")
    chapter_type: str = Field(..., description="Type: 'chapter', 'sub_chapter', or 'test'")
    order: int = Field(0, description="Display order within parent")


class QcManualChapterCreate(QcManualChapterBase):
    """Schema for creating a new chapter"""
    parent_chapter_id: Optional[uuid.UUID] = Field(None, description="Parent chapter ID for hierarchical structure")


class QcManualChapterUpdate(BaseModel):
    """Schema for updating a chapter"""
    title: Optional[str] = None
    content: Optional[Any] = None
    chapter_type: Optional[str] = None
    order: Optional[int] = None
    parent_chapter_id: Optional[uuid.UUID] = None


class QcManualChapterOut(QcManualChapterBase):
    """Schema for chapter output"""
    id: uuid.UUID
    manual_id: int
    parent_chapter_id: Optional[uuid.UUID]
    created_at: datetime
    created_by: str
    updated_at: Optional[datetime]
    updated_by: Optional[str]
    sub_chapters: List["QcManualChapterOut"] = Field(default_factory=list, description="Nested sub-chapters")

    class Config:
        from_attributes = True


# Resolve forward references for recursive model
QcManualChapterOut.model_rebuild()


class QcManualChapterTree(BaseModel):
    """Schema for chapter tree structure"""
    manual_id: int
    chapters: List[QcManualChapterOut]

    class Config:
        from_attributes = True
