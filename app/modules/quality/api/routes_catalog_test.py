from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.modules.quality.models.quality_manual import QualityManual
from app.modules.quality.models.qc_manual import QcManual
from app.modules.quality.models.qc_manual_chapter import QcManualChapter
from app.modules.quality.models.catalog_test import CatalogTest
from app.modules.quality.models.catalog_test_question import CatalogTestQuestion
from app.modules.quality.schemas.catalog_test import CatalogTestCreate, CatalogTestOut, CatalogTestUpdate
from app.modules.core.models.role import UserRole
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/catalog_tests", tags=["catalog-tests"])

def get_catalog_test_or_404(db: Session, test_id: UUID) -> CatalogTest:
    db_test = db.query(CatalogTest).filter(CatalogTest.id == test_id).first()
    if not db_test:
        raise HTTPException(status_code=404, detail="Catalog test not found")
    return db_test

@router.post("/",
             response_model=CatalogTestOut,
             status_code=201,
             dependencies =[Depends(require_roles(UserRole.ADMIN,UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def create(
        test_data: CatalogTestCreate,
        db: Session = Depends(get_db),
):
    try:
        new_test = CatalogTest(
            name=test_data.name,
            chapter=test_data.chapter,
            chapter_id=test_data.chapter_id,
            quality_manual_id=test_data.quality_manual_id,
            status=test_data.status
        )

        # Validate chapter exists in current Manual (Maintain legacy validation for now)
        # ...
        
        db.add(new_test)
        db.flush() # Get ID for questions
        
        if test_data.questions:
            for q in test_data.questions:
                new_question = CatalogTestQuestion(
                    catalog_test_id=new_test.id,
                    question=q.question,
                    specification=q.specification,
                    options=q.options,
                    type=q.type,
                    chapter_id=q.chapter_id # New: Store chapter link per question
                )
                db.add(new_question)
        
        db.commit()
        db.refresh(new_test)
        
        return new_test
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", 
             response_model=list[CatalogTestOut], 
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def get_all(db: Session = Depends(get_db)):
    return db.query(CatalogTest).all()


@router.patch("/{test_id}", 
               response_model=CatalogTestOut, 
               dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def update_catalog_test(test_id: UUID, test_data: CatalogTestUpdate, db: Session = Depends(get_db)):
    db_test = get_catalog_test_or_404(db, test_id)

    update_data = test_data.model_dump(exclude_unset=True)
    
    # Legacy validation removed to support relational linking

    for key, value in update_data.items():
        if key != "questions":
            setattr(db_test, key, value)

    # Handle questions synchronization
    if test_data.questions is not None:
        # Delete existing and recreate with new fields
        db.query(CatalogTestQuestion).filter(CatalogTestQuestion.catalog_test_id == test_id).delete()
        
        for q in test_data.questions:
            new_question = CatalogTestQuestion(
                catalog_test_id=test_id,
                question=q.question,
                specification=q.specification,
                options=q.options,
                type=q.type,
                chapter_id=q.chapter_id # Store chapter link per question
            )
            db.add(new_question)

    db.commit()
    db.refresh(db_test)
    
    return db_test

@router.delete("/{test_id}", 
               status_code=204, 
               dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def delete_catalog_test(test_id: UUID, db: Session = Depends(get_db)):
    db_test = get_catalog_test_or_404(db, test_id)
    db.delete(db_test)
    db.commit()
    return None