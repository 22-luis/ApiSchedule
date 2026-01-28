from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.shared.db.session import get_db
from app.modules.quality.models.code_test import CodeTest
from app.modules.codes.models.code import Code
from app.modules.quality.models.catalog_test import CatalogTest
from app.modules.quality.schemas.code_test import CodeTestLink, CodeTestOut
from app.modules.quality.schemas.catalog_test import CatalogTestOut
from app.modules.core.models.role import UserRole
from app.shared.utils.core.dependencies import require_roles
from app.modules.quality.models.qc_manual import QcManual
import unicodedata
import re

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/codes", tags=["codes"])

@router.post("/{code_id}/tests",   
             response_model=List[CatalogTestOut], 
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def link_tests_to_sync(
    code_id: UUID, 
    link_data: CodeTestLink, 
    db: Session = Depends(get_db)
):
    logger.info(f"Sincronizando pruebas para código {code_id}. Pruebas: {link_data.catalog_test_ids}")
    # Verify code exists
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        logger.error(f"Código {code_id} no encontrado")
        raise HTTPException(status_code=404, detail="Code not found")

    # Get current links
    current_links = db.query(CodeTest).filter(CodeTest.code_id == code_id).all()
    current_catalog_ids = {link.catalog_test_id for link in current_links}
    
    target_catalog_ids = set(link_data.catalog_test_ids)

    # Links to remove
    for link in current_links:
        if link.catalog_test_id not in target_catalog_ids:
            db.delete(link)
    
    # Links to add
    for test_id in target_catalog_ids:
        if test_id not in current_catalog_ids:
            # Verify test exists before adding
            test_exists = db.query(CatalogTest).filter(CatalogTest.id == test_id).first()
            if test_exists:
                db_link = CodeTest(
                    code_id=code_id,
                    catalog_test_id=test_id
                )
                db.add(db_link)
    
    db.commit()
    
    # Return all tests now linked to this code
    updated_tests = db.query(CatalogTest).join(
        CodeTest, CatalogTest.id == CodeTest.catalog_test_id
    ).filter(CodeTest.code_id == code_id).all()
    
    return enrich_tests_with_manual_content(db, updated_tests)

@router.get("/{code_id}/tests",   
             response_model=List[CatalogTestOut], 
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def get_tests_for_code(code_id: UUID, db: Session = Depends(get_db)):
    # Verify code exists
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    
    # Get all catalog tests linked to this code
    tests = db.query(CatalogTest).join(
        CodeTest, CatalogTest.id == CodeTest.catalog_test_id
    ).filter(CodeTest.code_id == code_id).all()
    
    # Enrich with manual content if applicable
    return enrich_tests_with_manual_content(db, tests)

def slugify(text: str) -> str:
    if not text: return ""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', text)

def enrich_tests_with_manual_content(db: Session, tests: List[CatalogTest]) -> List[dict]:
    try:
        # Obtener el último manual
        manual = db.query(QcManual).order_by(QcManual.id.desc()).first()
        if not manual or not manual.content:
            return [CatalogTestOut.model_validate(t, from_attributes=True).model_dump() for t in tests]

        content_dict = manual.content
        # Pre-calcular slugs del manual para eficiencia
        slug_map = {slugify(k): v for k, v in content_dict.items()}

        result = []
        for t in tests:
            # Populate manual_name for response
            if t.chapter_relation and t.chapter_relation.manual and t.chapter_relation.manual.quality_manual:
                t.manual_name = t.chapter_relation.manual.quality_manual.name
            
            test_data = CatalogTestOut.model_validate(t).model_dump()
            result.append(test_data)
        
        return result
    except Exception as e:
        logger.error(f"Error enriqueciendo pruebas: {str(e)}", exc_info=True)
        # Fallback a datos básicos si falla el enriquecimiento
        return [CatalogTestOut.model_validate(t, from_attributes=True).model_dump() for t in tests]

@router.delete("/{code_id}/tests/{test_id}", 
               status_code=204, 
               dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def unlink_test_from_code(
    code_id: UUID, 
    test_id: UUID, 
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR))
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

@router.get("/by_code_string/{code}/tests", 
             response_model=List[CatalogTestOut], 
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def get_tests_by_code_string(code: str, db: Session = Depends(get_db)):
    # Find code by string
    code_obj = db.query(Code).filter(Code.code == code).first()
    if not code_obj:
        raise HTTPException(status_code=404, detail="Code not found")
    
    # Get tests linked to this code
    tests = db.query(CatalogTest).join(
        CodeTest, CatalogTest.id == CodeTest.catalog_test_id
    ).filter(CodeTest.code_id == code_obj.id).all()
    
    return enrich_tests_with_manual_content(db, tests)
