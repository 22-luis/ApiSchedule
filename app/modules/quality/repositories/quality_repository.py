from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from typing import List, Optional
import uuid

from app.modules.quality.models.qc_manual_chapter import QcManualChapter
from app.modules.quality.models.quality_manual import QualityManual
from app.modules.quality.models.qc_manual import QcManual

# Manual Chapters
def find_chapter_by_id(db: Session, chapter_id: uuid.UUID) -> Optional[QcManualChapter]:
    return db.query(QcManualChapter).filter(QcManualChapter.id == chapter_id).first()

def find_chapters_by_manual(db: Session, manual_id: int) -> List[QcManualChapter]:
    return db.query(QcManualChapter).filter(QcManualChapter.manual_id == manual_id).all()

def find_root_chapters_with_subchapters(db: Session, manual_id: int) -> List[QcManualChapter]:
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
    return list(result.scalars().all())

def save_chapter(db: Session, chapter: QcManualChapter) -> QcManualChapter:
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter

def delete_chapter(db: Session, chapter: QcManualChapter):
    db.delete(chapter)
    db.commit()

# Manuals
def find_manual_by_id(db: Session, manual_id: int) -> Optional[QualityManual]:
    return db.query(QualityManual).filter(QualityManual.id == manual_id).first()

def save_manual(db: Session, manual: QualityManual) -> QualityManual:
    db.add(manual)
    db.commit()
    db.refresh(manual)
    return manual

def find_manual_by_name(db: Session, name: str) -> Optional[QualityManual]:
    return db.query(QualityManual).filter(QualityManual.name == name).first()

def save_qc_manual(db: Session, qc_manual: QcManual) -> QcManual:
    db.add(qc_manual)
    db.commit()
    db.refresh(qc_manual)
    return qc_manual

def find_latest_qc_manual_by_quality_manual(db: Session, quality_manual_id: int) -> Optional[QcManual]:
    return db.query(QcManual).filter(QcManual.quality_manual_id == quality_manual_id).order_by(QcManual.id.desc()).first()

def find_qc_manual_by_id(db: Session, qc_manual_id: int) -> Optional[QcManual]:
    return db.query(QcManual).filter(QcManual.id == qc_manual_id).first()

def find_manuals_ordered(db: Session) -> List[QualityManual]:
    return db.query(QualityManual).order_by(QualityManual.order).all()

def find_latest_qc_manual_by_name(db: Session, name: str) -> Optional[QcManual]:
    return db.query(QcManual).join(QualityManual).filter(QualityManual.name == name).order_by(QcManual.id.desc()).first()
