import uuid
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.modules.quality.models.qc_manual_chapter import QcManualChapter
from app.modules.quality.schemas.qc_manual_chapter import (
    QcManualChapterCreate,
    QcManualChapterUpdate
)


def create_chapter(
    db: Session,
    manual_id: int,
    chapter_data: QcManualChapterCreate,
    user: str
) -> QcManualChapter:
    """Create a new chapter with audit information"""
    chapter = QcManualChapter(
        manual_id=manual_id,
        parent_chapter_id=chapter_data.parent_chapter_id,
        title=chapter_data.title,
        content=chapter_data.content,
        chapter_type=chapter_data.chapter_type,
        order=chapter_data.order,
        created_by=user
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


def update_chapter(
    db: Session,
    chapter_id: uuid.UUID,
    chapter_data: QcManualChapterUpdate,
    user: str
) -> Optional[QcManualChapter]:
    """Update a chapter and set updated_by/updated_at"""
    chapter = db.query(QcManualChapter).filter(QcManualChapter.id == chapter_id).first()
    if not chapter:
        return None
    
    update_data = chapter_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chapter, field, value)
    
    chapter.updated_by = user
    db.commit()
    db.refresh(chapter)
    return chapter


def delete_chapter(db: Session, chapter_id: uuid.UUID) -> bool:
    """Delete a chapter and cascade to sub-chapters"""
    chapter = db.query(QcManualChapter).filter(QcManualChapter.id == chapter_id).first()
    if not chapter:
        return False
    
    db.delete(chapter)
    db.commit()
    return True


def get_chapter_tree(db: Session, manual_id: int) -> List[QcManualChapter]:
    """Retrieve full chapter hierarchy for a manual (only root chapters with nested sub-chapters)"""
    stmt = (
        select(QcManualChapter)
        .where(
            QcManualChapter.manual_id == manual_id,
            QcManualChapter.parent_chapter_id.is_(None)
        )
        .order_by(QcManualChapter.order)
        .options(selectinload(QcManualChapter.sub_chapters))
    )
    
    result = db.execute(stmt)
    chapters = result.scalars().all()
    return list(chapters)


def get_chapter_by_id(db: Session, chapter_id: uuid.UUID) -> Optional[QcManualChapter]:
    """Get a single chapter by ID"""
    return db.query(QcManualChapter).filter(QcManualChapter.id == chapter_id).first()


def reorder_chapters(
    db: Session,
    chapter_orders: List[dict]
) -> bool:
    """Update display order for multiple chapters
    
    Args:
        chapter_orders: List of dicts with 'id' and 'order' keys
    """
    try:
        for item in chapter_orders:
            chapter = db.query(QcManualChapter).filter(
                QcManualChapter.id == item['id']
            ).first()
            if chapter:
                chapter.order = item['order']
        
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False


def create_chapters_from_hierarchy(
    db: Session,
    manual_id: int,
    hierarchy: List[dict],
    user: str,
    parent_id: Optional[uuid.UUID] = None,
    base_order: int = 0
) -> List[QcManualChapter]:
    """
    Recursively create chapters from hierarchical structure
    
    Args:
        hierarchy: List of chapter dictionaries with 'title', 'content', 'sub_chapters', 'tests'
        parent_id: Parent chapter UUID for nested chapters
        base_order: Starting order number
    """
    created_chapters = []
    
    for idx, chapter_data in enumerate(hierarchy):
        # Create main chapter
        chapter = QcManualChapter(
            manual_id=manual_id,
            parent_chapter_id=parent_id,
            title=chapter_data.get('title', ''),
            content=chapter_data.get('content', ''),
            chapter_type='chapter' if parent_id is None else 'sub_chapter',
            order=base_order + idx,
            created_by=user
        )
        db.add(chapter)
        db.flush()  # Get the ID without committing
        
        # Sincronizar ID generado de vuelta a la estructura de la jerarquía
        chapter_data['id'] = str(chapter.id)
        
        created_chapters.append(chapter)
        
        # Create sub-chapters recursively
        sub_chapters = chapter_data.get('sub_chapters', [])
        if sub_chapters:
            sub_created = create_chapters_from_hierarchy(
                db, manual_id, sub_chapters, user, chapter.id, 0
            )
            created_chapters.extend(sub_created)
        
        # Create tests as special sub-chapters
        tests = chapter_data.get('tests', [])
        for test_idx, test_data in enumerate(tests):
            test_chapter = QcManualChapter(
                manual_id=manual_id,
                parent_chapter_id=chapter.id,
                title=test_data.get('title', ''),
                content=test_data.get('content', ''),
                chapter_type='test',
                order=test_idx,
                created_by=user
            )
            db.add(test_chapter)
            db.flush()
            
            # Sincronizar ID de la prueba
            test_data['id'] = str(test_chapter.id)
            
            created_chapters.append(test_chapter)
    
    return created_chapters
