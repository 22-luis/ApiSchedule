import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.codes.models.codeVerification import CodeVerification

from app.modules.codes.models.code import Code

def find_by_id(db: Session, verification_id: uuid.UUID) -> Optional[CodeVerification]:
    return db.query(CodeVerification).filter(verification_id == CodeVerification.id).first()

def find_all(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> list[CodeVerification]:

    query = db.query(CodeVerification)
    if search:
        query = query.join(Code, CodeVerification.codeId == Code.id)
        pattern = f"%{search.lower()}%"
        query = query.filter(
            Code.code.ilike(pattern) | Code.description.ilike(pattern)
        )
    verifications = query.offset(skip).limit(limit).all()
    return verifications

def save(db: Session, code: CodeVerification, flush: bool = False) -> CodeVerification:
    db.add(code)
    if flush:
        db.flush()
    else:
        db.commit()
        db.refresh(code)
    return code


def delete(db: Session, code: CodeVerification) -> None:
    db.delete(code)


def commit(db: Session) -> None:
    db.commit()
