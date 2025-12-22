from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.test import Test
from app.modules.quality.models.qc_manual import QcManual
from app.modules.quality.schemas.test import TestCreate, TestOut
from app.modules.quality.schemas.qc_manual import QcManualCreate, QcManualOut
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/quality", tags=["quality"])

@router.post("/test", response_model=TestOut, status_code=201)
def create_test_record(
    test_data: TestCreate, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        new_test = Test(
            lote=test_data.lote,
            status=test_data.status,
            results=test_data.results
        )
        db.add(new_test)
        db.commit()
        db.refresh(new_test)
        return new_test
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un registro de calidad para el lote {test_data.lote} o el lote no es válido."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/manual", response_model=QcManualOut, status_code=201)
def create_qc_manual(
    manual_data: QcManualCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        new_manual = QcManual(
            content=manual_data.content,
            version=0,
            created_by=current_user.username
        )
        db.add(new_manual)
        db.flush()
        new_manual.version = new_manual.id
        db.commit()
        db.refresh(new_manual)
        return new_manual
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/manual/latest", response_model=QcManualOut)
def get_latest_qc_manual(db: Session = Depends(get_db)):
    manual = db.query(QcManual).order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    return manual
