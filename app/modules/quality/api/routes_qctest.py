from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.test_record import TestRecord as Test
from app.modules.quality.models.test_results import TestResults
from app.modules.quality.models.test_status import TestStatus
from app.modules.quality.schemas.test_record import TestSessionCreate, TestSessionOut, TestUpdate
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/qctest", tags=["qctest"])

@router.get("/session/{lote}/{code_id}", response_model=TestSessionOut)
def get_session(lote: int, code_id: UUID, db: Session = Depends(get_db), _current_user = Depends(get_current_user)):
    session = db.query(Test).filter(Test.lote == lote, Test.code_id == code_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Quality session not found")
    return session

@router.post("/session", response_model=TestSessionOut)
def save_session(
    session_data: TestSessionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        # Check if session already exists
        session = db.query(Test).filter(Test.lote == session_data.lote, Test.code_id == session_data.code_id).first()
        
        if not session:
            # Create new session
            session = Test(
                lote=session_data.lote,
                code_id=session_data.code_id,
                status=TestStatus.pending, # Mark as pending when first saved with results
                performed_by=current_user.username if hasattr(current_user, 'username') else str(current_user.id),
                performed_at=datetime.now(),
                comment=session_data.comment
            )
            db.add(session)
            db.flush() # Get session ID
        else:
            # Update existing session metadata
            session.performed_by = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
            session.performed_at = datetime.now()
            session.comment = session_data.comment
            session.status = TestStatus.pending # Re-mark as pending for re-review if updated

        # Update or create results
        for res in session_data.results:
            existing_res = db.query(TestResults).filter(
                TestResults.test_record_id == session.id,
                TestResults.catalog_test_id == res.catalog_test_id
            ).first()
            
            if existing_res:
                existing_res.answer = res.answer
            else:
                new_res = TestResults(
                    test_record_id=session.id,
                    catalog_test_id=res.catalog_test_id,
                    answer=res.answer
                )
                db.add(new_res)
        
        db.commit()
        db.refresh(session)
        return session
        
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error saving quality session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/session/{session_id}/status", response_model=TestSessionOut)
def update_session_status(
    session_id: UUID,
    status_update: TestUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    session = db.query(Test).filter(Test.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Quality session not found")
    
    if status_update.status:
        session.status = status_update.status
        if status_update.status == TestStatus.accepted:
            session.approved_by = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
            session.approved_at = datetime.now()
    
    if status_update.comment:
        session.comment = status_update.comment
        
    db.commit()
    db.refresh(session)
    return session

@router.get("/{lote}", response_model=TestSessionOut)
def get_test_record_by_lote(
    lote: int,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    # This remains for backward compatibility but returns the full session (first one found for the lote)
    test_record = db.query(Test).filter(Test.lote == lote).first()
    if not test_record:
        raise HTTPException(status_code=404, detail="Registro de calidad no encontrado")
    return test_record

