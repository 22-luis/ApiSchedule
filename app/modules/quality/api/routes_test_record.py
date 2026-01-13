from uuid import UUID

from fastapi.params import Depends
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.modules.core.models.role import UserRole
from app.modules.quality.models.test_record import TestRecord
from app.modules.quality.schemas.test_record import TestOut, TestUpdate
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/test_record", tags=["test-record"])

@router.post("/",
             response_model=TestOut,
             status_code=201,
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def create_test_record(test_data: TestOut, db: Session = Depends(get_db)):
    try:
        new_record = TestRecord(
            lote=test_data.lote,
            catalog_test=test_data.catalog_test,
            status=test_data.status,
            performed_by=test_data.performed_by,
            performed_at=test_data.performed_at,
            approved_by=test_data.approved_by,
            approved_at=test_data.approved_at,
            comment=test_data.comment
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{test_id}",
              response_model=TestOut,
              status_code=200,
              dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def update_test_record(test_id: UUID, test_data: TestUpdate, db: Session = Depends(get_db)):
    db_test = db.query(TestRecord).filter(TestRecord.id == test_id).first()

    if not db_test:
        raise HTTPException(status_code=404, detail="Registro de calidad no encontrado")

    update_data = test_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_test, field, value)

    db.commit()
    db.refresh(db_test)
    return db_test

@router.get("/{test_id}", response_model=TestOut, status_code=200, dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))],)
def get_test_record(test_id: UUID, db: Session = Depends(get_db)):
    test_record = db.query(TestRecord).filter(TestRecord.id == test_id).first()
    return test_record