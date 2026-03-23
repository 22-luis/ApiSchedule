import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.codes.models.codeVerification import CodeVerification
from app.modules.codes.repositories import codeVerificationRepository
from app.modules.codes.schemas.codeVerification import CodeVerificationSchema, CodeVerificationOut

def create_verification(db: Session, verification: CodeVerificationSchema) -> CodeVerificationOut:
    db_verification = CodeVerification(**verification.model_dump())
    return codeVerificationRepository.save(db, db_verification)

def get_verifications(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> list[CodeVerification]:
    verifications = codeVerificationRepository.find_all(db, skip=skip, limit=limit, search=search)
    return verifications

def update_verification(db: Session, verification_id: uuid.UUID, verification_update: CodeVerificationSchema) -> CodeVerificationOut:
    db_verification = codeVerificationRepository.find_by_id(db, verification_id)
    if not db_verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    for field, value in verification_update.model_dump(exclude_unset=True).items():
        setattr(db_verification, field, value)

    codeVerificationRepository.commit(db)
    db.refresh(db_verification)
    return db_verification

def delete_verification(db: Session, verification_id: uuid.UUID) -> None:
    db_verification = codeVerificationRepository.find_by_id(db, verification_id)
    if not db_verification:
        raise HTTPException(status_code=404, detail="Verification not found")
    codeVerificationRepository.delete(db, db_verification)
    codeVerificationRepository.commit(db)
    return None


def verificationService():
    return None