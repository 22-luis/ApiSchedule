from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.shared.db.session import get_db
from app.shared.utils.core.time_utils import TimeZoneUtils
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.test_record import TestRecord as Test
from app.modules.quality.schemas.test_record import TestCreate, TestUpdate, TestOut, TestSessionCreate, TestSessionOut
from app.modules.quality.models.test_results import TestResults
from app.modules.organization.models.role import UserRole
from app.modules.quality.models.test_status import TestStatus
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, extract
import base64
from app.modules.organization.models.user import User as UserModel

router = APIRouter(prefix="/qctest", tags=["qctest"])

def get_next_analysis_number(db: Session) -> int:
    """Gets the next sequential analysis number for the current month."""
    now = TimeZoneUtils.get_now()
    year = now.year
    month = now.month
    
    # Get the maximum analysis_number for the current month and year
    max_num = db.query(func.max(Test.analysis_number)).filter(
        extract('year', Test.performed_at) == year,
        extract('month', Test.performed_at) == month
    ).scalar()
    
    if max_num is None:
        return 1
    return max_num + 1

@router.get("/session/{lote}/{code_id}", response_model=TestSessionOut)
def get_session(lote: int, code_id: UUID, db: Session = Depends(get_db), _current_user = Depends(get_current_user)):
    session = db.query(Test).options(joinedload(Test.results)).filter(Test.lote == lote, Test.code_id == code_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Quality session not found")
    
    # Enrich with user details
    enrich_session_user_details(session, db)
    return session

def enrich_session_user_details(session, db: Session):
    if session.performed_by:
        performer = db.query(UserModel).filter(UserModel.username == session.performed_by).first()
        if performer:
            session.performer_details = {
                "username": performer.username,
                "full_name": performer.full_name,
                "cargo": performer.cargo,
                "signature": base64.b64encode(performer.signature).decode('utf-8') if performer.signature else None,
                "document_name": performer.document_name,
                "role": performer.role.value if hasattr(performer.role, 'value') else str(performer.role)
            }
    
    if session.approved_by:
        authorizer = db.query(UserModel).filter(UserModel.username == session.approved_by).first()
        if authorizer:
            session.authorizer_details = {
                "username": authorizer.username,
                "full_name": authorizer.full_name,
                "cargo": authorizer.cargo,
                "signature": base64.b64encode(authorizer.signature).decode('utf-8') if authorizer.signature else None,
                "document_name": authorizer.document_name,
                "role": authorizer.role.value if hasattr(authorizer.role, 'value') else str(authorizer.role)
            }

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
                performed_at=TimeZoneUtils.get_now(),
                comment=session_data.comment,
                analysis_number=get_next_analysis_number(db)
            )
            db.add(session)
            db.flush() # Get session ID
        else:
            # Update existing session metadata
            session.performed_by = current_user.username if hasattr(current_user, 'username') else str(current_user.id)
            session.performed_at = TimeZoneUtils.get_now()
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
        enrich_session_user_details(session, db)
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
    test_record = db.query(Test).filter(Test.id == session_id).first()
    if not test_record:
        raise HTTPException(status_code=404, detail="Registro de calidad no encontrado")
    try:
        update_data = status_update.model_dump(exclude_unset=True)
        
        # Security Check: Only QC_COORDINATOR or ADMIN can accept/approve
        if "status" in update_data and update_data["status"] == TestStatus.accepted:
             if current_user.role not in [UserRole.QC_COORDINATOR, UserRole.ADMIN]:
                 raise HTTPException(status_code=403, detail="Only QC Coordinators or Admins can approve tests.")
             
             # Auto-set approval fields
             test_record.approved_by = current_user.username
             test_record.approved_at = TimeZoneUtils.get_now()

        for key, value in update_data.items():
            setattr(test_record, key, value)
        db.commit()
        db.refresh(test_record)
        enrich_session_user_details(test_record, db)
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

@router.get("/{lote}", response_model=TestSessionOut)
def get_test_record_by_lote(
    lote: int,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    # This remains for backward compatibility but returns the full session (first one found for the lote)
    test_record = db.query(Test).options(joinedload(Test.results)).filter(Test.lote == lote).first()
    if not test_record:
        raise HTTPException(status_code=404, detail="Registro de calidad no encontrado")
    enrich_session_user_details(test_record, db)
    return test_record

