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
            status=test_data.status
        )

        # Validate chapter exists in current Manual
        # Join with QualityManual to find the latest revision
        latest_manual = db.query(QcManual).join(QualityManual).order_by(QcManual.id.desc()).first()
        if not latest_manual:
             raise HTTPException(status_code=400, detail="No QC Manual found. Cannot create test without a manual.")
        
        # Fetch all chapter titles for this manual revision
        valid_chapters = [c.title for c in db.query(QcManualChapter.title).filter(QcManualChapter.manual_id == latest_manual.id).all()]
        
        # Normalize for comparison? strict comparison for now as per requirement for reliability
        if test_data.chapter not in valid_chapters:
             raise HTTPException(status_code=400, detail=f"Chapter '{test_data.chapter}' not found in current Manual. Available: {valid_chapters}")

        db.add(new_test)
        db.flush() # Get ID for questions
        
        if test_data.questions:
            for q in test_data.questions:
                new_question = CatalogTestQuestion(
                    catalog_test_id=new_test.id,
                    question=q.question,
                    specification=q.specification,
                    type=q.type
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
    
    # If chapter is being updated, validate it
    if "chapter" in update_data:
         latest_manual = db.query(QcManual).join(QualityManual).order_by(QcManual.id.desc()).first()
         if not latest_manual:
             raise HTTPException(status_code=400, detail="No QC Manual found.")
         
         valid_chapters = [c.title for c in db.query(QcManualChapter.title).filter(QcManualChapter.manual_id == latest_manual.id).all()]
         
         if update_data["chapter"] not in valid_chapters:
             raise HTTPException(status_code=400, detail=f"Chapter '{update_data['chapter']}' not found in current Manual.")

    for key, value in update_data.items():
        if key != "questions":
            setattr(db_test, key, value)

    # Handle questions synchronization
    if test_data.questions is not None:
        # Simplest approach: delete existing and recreate
        # (Could be optimized to update existing, but this ensures strict sync with frontend state)
        db.query(CatalogTestQuestion).filter(CatalogTestQuestion.catalog_test_id == test_id).delete()
        
        for q in test_data.questions:
            new_question = CatalogTestQuestion(
                catalog_test_id=test_id,
                question=q.question,
                specification=q.specification,
                type=q.type
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