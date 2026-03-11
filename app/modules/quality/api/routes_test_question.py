from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.organization.models.role import UserRole
from app.modules.quality.models.catalog_test_question import CatalogTestQuestion
from app.modules.quality.schemas.catalog_test_question import CatalogTestQuestionCreate, CatalogTestQuestionUpdate, CatalogTestQuestionOut
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/test-question", tags=["test-question"])

@router.post("/", response_model=CatalogTestQuestionOut, status_code=201, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def create_question(
        test_data: CatalogTestQuestionCreate, 
        db: Session = Depends(get_db)
):
    try:
        new_question = CatalogTestQuestion(
            catalog_test_id=test_data.catalog_test_id,
            question=test_data.question,
            specification=test_data.specification,
            type=test_data.type
        )
        db.add(new_question)
        db.commit()
        db.refresh(new_question)
        return new_question
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{test_id}",
            response_model=list[CatalogTestQuestionOut],
            status_code=200,
            dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def get_questions_for_test(
        test_id: UUID,
        db: Session = Depends(get_db)
):
    test_questions = db.query(CatalogTestQuestion).filter(CatalogTestQuestion.catalog_test_id == test_id).all()
    return test_questions

@router.patch("/{question_id}",
            response_model=CatalogTestQuestionOut,
            status_code=200,
            dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def update_question(
        question_id: UUID,
        question_data: CatalogTestQuestionUpdate,
        db: Session = Depends(get_db)
):
    test_question = db.query(CatalogTestQuestion).filter(CatalogTestQuestion.id == question_id).first()
    if not test_question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    try:
        update_data = question_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(test_question, key, value)
        db.commit()
        db.refresh(test_question)
        return test_question
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Error de integridad al actualizar la pregunta")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{question_id}", status_code=204, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def delete_question(question_id: UUID, db: Session = Depends(get_db)):
    db_question = db.query(CatalogTestQuestion).filter(CatalogTestQuestion.id == question_id).first()
    if not db_question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    db.delete(db_question)
    db.commit()
    return None