from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.shared.db.session import get_db
from app.modules.codes.models.code_test import CodeTest
from app.modules.codes.models.code import Code
from app.modules.codes.models.catalog_test import CatalogTest
from app.modules.codes.schemas.code_test import CodeTestLink, CodeTestOut
from app.modules.codes.schemas.catalog_test import CatalogTestOut
from app.modules.core.models.role import UserRole
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/codes/{code_id}/tests", tags=["codes"])

@router.post("/", response_model=List[CodeTestOut])
def link_tests_to_code(
    code_id: UUID, 
    link_data: CodeTestLink, 
    db: Session = Depends(get_db),
    current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_ENGINEER))
):
    # Verify code exists
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")

    new_links = []
    for test_id in link_data.catalog_test_ids:
        # Verify test exists
        test = db.query(CatalogTest).filter(CatalogTest.id == test_id).first()
        if not test:
            continue
        
        # Check if already linked
        existing = db.query(CodeTest).filter(
            CodeTest.code_id == code_id, 
            CodeTest.catalog_test_id == test_id
        ).first()
        
        if not existing:
            db_link = CodeTest(
                code_id=code_id,
                catalog_test_id=test_id
            )
            db.add(db_link)
            new_links.append(db_link)
    
    db.commit()
    for link in new_links:
        db.refresh(link)
    
    return new_links

@router.get("/", response_model=List[CatalogTestOut])
def get_tests_for_code(code_id: UUID, db: Session = Depends(get_db)):
    # Verify code exists
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    
    # Get all catalog tests linked to this code
    tests = db.query(CatalogTest).join(
        CodeTest, CatalogTest.id == CodeTest.catalog_test_id
    ).filter(CodeTest.code_id == code_id).all()
    
    return tests

@router.delete("/{test_id}", status_code=204)
def unlink_test_from_code(
    code_id: UUID, 
    test_id: UUID, 
    db: Session = Depends(get_db),
    current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_ENGINEER))
):
    link = db.query(CodeTest).filter(
        CodeTest.code_id == code_id, 
        CodeTest.catalog_test_id == test_id
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    db.delete(link)
    db.commit()
    return None

@router.get("/by_code_string/{code}/tests", response_model=List[CatalogTestOut])
def get_tests_by_code_string(code: str, db: Session = Depends(get_db)):
    # Find code by string
    code_obj = db.query(Code).filter(Code.code == code).first()
    if not code_obj:
        raise HTTPException(status_code=404, detail="Code not found")
    
    # Use existing logic to get tests
    tests = db.query(CatalogTest).join(
        CodeTest, CatalogTest.id == CodeTest.catalog_test_id
    ).filter(CodeTest.code_id == code_obj.id).all()
    
    return tests
