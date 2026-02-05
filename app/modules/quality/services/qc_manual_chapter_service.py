import uuid
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from app.modules.quality.models.qc_manual_chapter import QcManualChapter
from app.modules.quality.models.quality_manual import QualityManual
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


def reorder_manuals(
    db: Session,
    manual_orders: List[dict]
) -> bool:
    """Update display order for multiple quality manuals
    
    Args:
        manual_orders: List of dicts with 'id' and 'order' keys
    """
    try:
        for item in manual_orders:
            manual = db.query(QualityManual).filter(
                QualityManual.id == item['id']
            ).first()
            if manual:
                manual.order = item['order']
        
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

def sync_chapters_from_hierarchy(
    db: Session,
    manual_id: int,
    hierarchy: List[dict],
    user: str
):
    """
    Synchronize the database chapters with the incoming hierarchy.
    - Update existing chapters if ID matches.
    - Create new chapters if ID is new/missing.
    - Delete chapters that are no longer in the hierarchy.
    """
    # 1. Get all existing chapters to track deletions
    existing_chapters = db.query(QcManualChapter).filter(QcManualChapter.manual_id == manual_id).all()
    existing_map = {str(ch.id): ch for ch in existing_chapters}
    processed_ids = set()

    def process_node(nodes, parent_id=None, base_order=0):
        for idx, node_data in enumerate(nodes):
            node_id = str(node_data.get('id', ''))
            
            # Check if it's a valid UUID and exists
            chapter = None
            if node_id in existing_map:
                chapter = existing_map[node_id]
            
            if chapter:
                # UPDATE
                chapter.title = node_data.get('title', chapter.title)
                chapter.content = node_data.get('content', chapter.content)
                chapter.order = base_order + idx
                chapter.parent_chapter_id = parent_id
                # Only update type if it's not a test (tests are handled separately below usually, but check structure)
                # The hierarchy passed often has 'sub_chapters' and 'tests'.
                # A node in 'sub_chapters' is chapter/sub_chapter.
                chapter.chapter_type = 'chapter' if parent_id is None else 'sub_chapter'
                chapter.updated_by = user
                processed_ids.add(str(chapter.id))
            else:
                # CREATE
                # Note: node_id might be a temporary ID from frontend (e.g. "h1-0-title"). 
                # We ignore it and let DB generate new UUID.
                chapter = QcManualChapter(
                    manual_id=manual_id,
                    parent_chapter_id=parent_id,
                    title=node_data.get('title', ''),
                    content=node_data.get('content', ''),
                    chapter_type='chapter' if parent_id is None else 'sub_chapter',
                    order=base_order + idx,
                    created_by=user
                )
                db.add(chapter)
                db.flush() # Get ID
                processed_ids.add(str(chapter.id))
            
            # Recurse for sub-chapters
            if 'sub_chapters' in node_data and node_data['sub_chapters']:
                 process_node(node_data['sub_chapters'], chapter.id, 0)
            
            # Handle tests (as special chapters)
            # hierarchy structure usually separates 'tests' list
            if 'tests' in node_data and node_data['tests']:
                 for t_idx, t_node in enumerate(node_data['tests']):
                      t_id = str(t_node.get('id', ''))
                      t_chapter = None
                      if t_id in existing_map:
                           t_chapter = existing_map[t_id]
                      
                      if t_chapter:
                           # Update Test
                           t_chapter.title = t_node.get('title', t_chapter.title)
                           t_chapter.content = t_node.get('content', t_chapter.content)
                           t_chapter.order = t_idx
                           t_chapter.parent_chapter_id = chapter.id
                           t_chapter.chapter_type = 'test'
                           t_chapter.updated_by = user
                           processed_ids.add(str(t_chapter.id))
                      else:
                           # Create Test
                           t_chapter = QcManualChapter(
                                manual_id=manual_id,
                                parent_chapter_id=chapter.id,
                                title=t_node.get('title', ''),
                                content=t_node.get('content', ''),
                                chapter_type='test',
                                order=t_idx,
                                created_by=user
                           )
                           db.add(t_chapter)
                           db.flush()
                           processed_ids.add(str(t_chapter.id))

    process_node(hierarchy, None, 0)

    # Delete unprocessed chapters
    # Note: We need to be careful about cascade delete. 
    # If we delete a parent, children are deleted. 
    # But strictly speaking, if a child was processed, it shouldn't be deleted.
    # However, if a child was moved to a new parent, it would be processed (updated).
    # So unprocessed IDs are genuinely removed.
    for ch_id, ch in existing_map.items():
        if ch_id not in processed_ids:
            db.delete(ch)
