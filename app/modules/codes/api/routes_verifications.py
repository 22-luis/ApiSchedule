import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.codes.services import codeVerificationService
from app.modules.codes.schemas.codeVerification import CodeVerificationSchema, CodeVerificationOut
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.shared.utils.core.dependencies import require_roles
from app.shared.db.session import get_db

router = APIRouter(prefix="/verifications", tags=["verifications"])

@router.post("/", response_model=CodeVerificationOut)
def create_verification(
    verification: CodeVerificationSchema,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return codeVerificationService.create_verification(db, verification)

@router.get("/", response_model=List[CodeVerificationOut])
def get_verifications(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de registros a devolver"),
    search: str = Query(None, description="Buscar por código o descripción"),
    _current_user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER)
    )
):
    return codeVerificationService.get_verifications(db, skip=skip, limit=limit, search=search)

@router.patch("/{verification_id}", response_model=CodeVerificationOut)
def update_verification(
    verification_id: uuid.UUID,
    verification: CodeVerificationSchema,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return codeVerificationService.update_verification(db, verification_id, verification)

@router.delete("/{verification_id}")
def delete_verification(
    verification_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    codeVerificationService.delete_verification(db, verification_id)
    return {"detail": "Verification deleted successfully"}