from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.modules.core.models.role import UserRole
from app.modules.quality.models.test_results import TestResults
from app.modules.quality.schemas.test_results import TestResultsOut, TestResultsCreate, TestResultsUpdate
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/test_results", tags=["test-results"])

@router.post("/",
             response_model=TestResultsOut,
             status_code=201,
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def create_test_result(
        result_data: TestResultsOut,
        db: Session = Depends(get_db)
):
    try:
        new_result = TestResults(
            test_record_id=result_data.test_record_id,
            catalog_test_id=result_data.catalog_test_id,
            answer=result_data.answer
        )
        db.add(new_result)
        db.commit()
        db.refresh(new_result)
        return new_result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{result_id}",
              status_code=200,
              dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def update_test_result(
        result_id: UUID,
        result_data: TestResultsUpdate,
        db: Session = Depends(get_db)
):
    test_result = db.query(TestResults).filter(TestResults.id == result_id).first()
    if not test_result:
        raise HTTPException(status_code=404, detail="Resultado de prueba no encontrado")
    try:
        update_data = result_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(test_result, field, value)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{result_id}",
            status_code=200,
            dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def get_test_result(
        result_id: UUID,
        db: Session = Depends(get_db)
):
    test_result = db.query(TestResults).filter(TestResults.id == result_id).first()
    return test_result