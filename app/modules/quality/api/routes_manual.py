from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.qc_manual import QcManual
from app.modules.quality.schemas.qc_manual import QcManualCreate, QcManualOut

router = APIRouter(prefix="/manual", tags=["manual"])

@router.post("/", response_model=QcManualOut, status_code=201)
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

@router.get("/latest", response_model=QcManualOut)
def get_latest_qc_manual(db: Session = Depends(get_db)):
    manual = db.query(QcManual).order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    return manual
