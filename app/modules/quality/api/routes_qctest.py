from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.test import Test
from app.modules.quality.schemas.test import TestCreate, TestUpdate, TestOut
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/qctest", tags=["qctest"])

@router.post("/", response_model=TestOut, status_code=201)
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
    
    
@router.patch("/{test_id}", response_model=TestOut)
def update_test_record(
    test_id: str,
    test_data: TestUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    test_record = db.query(Test).filter(Test.id == test_id).first()
    if not test_record:
        raise HTTPException(status_code=404, detail="Registro de calidad no encontrado")
    try:
        if test_data.status is not None:
            test_record.status = test_data.status
        if test_data.results is not None:
            test_record.results = test_data.results
        db.commit()
        db.refresh(test_record)
        return test_record
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"Error de integridad al actualizar el registro de calidad."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))    

@router.get("/{test_id}", response_model=TestOut)
def get_test_record(
    test_id: str,
    db: Session = Depends(get_db)
):
    test_record = db.query(Test).filter(Test.id == test_id).first()
    if not test_record:
        raise HTTPException(status_code=404, detail="Registro de calidad no encontrado")
    return test_record