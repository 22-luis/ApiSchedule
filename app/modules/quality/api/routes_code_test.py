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
from app.modules.organization.models.role import UserRole
from app.shared.utils.core.dependencies import require_roles
from app.modules.quality.models.code_test_parameter_specification import CodeTestParameterSpecification
from app.modules.quality.schemas.code_test_parameter_specification import CodeTestParameterSpecificationBatch
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
    
    return enrich_tests_with_manual_content(db, updated_tests, code_id=code_id)

@router.post("/{code_id}/specifications",
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def save_code_specifications(
    code_id: UUID,
    batch_data: CodeTestParameterSpecificationBatch,
    db: Session = Depends(get_db)
):
    logger.info(f"Guardando especificaciones para código {code_id}")
    
    # Verify code exists
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")

    for spec in batch_data.specifications:
        # We assume the user sends specifications for questions related to tests linked to this code
        # We can add more validation if needed
        existing = db.query(CodeTestParameterSpecification).filter(
            CodeTestParameterSpecification.code_id == code_id,
            CodeTestParameterSpecification.question_id == spec.question_id
        ).first()
        
        if existing:
            existing.specification = spec.specification
        else:
            db_spec = CodeTestParameterSpecification(
                code_id=code_id,
                question_id=spec.question_id,
                specification=spec.specification
            )
            db.add(db_spec)
            
    db.commit()
    return {"status": "success"}

from sqlalchemy.orm import Session, joinedload
from app.modules.quality.models.qc_manual_chapter import QcManualChapter
from app.modules.quality.models.qc_manual import QcManual

# ... imports ...

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
    ).filter(CodeTest.code_id == code_id).options(
        joinedload(CatalogTest.chapter_relation).joinedload(QcManualChapter.manual).joinedload(QcManual.quality_manual),
        joinedload(CatalogTest.quality_manual),
        joinedload(CatalogTest.questions)
    ).all()
    
    
    # Enrich with manual content if applicable
    return enrich_tests_with_manual_content(db, tests, code_id=code_id)

def enrich_tests_with_manual_content(db: Session, tests: List[CatalogTest], code_id: UUID = None) -> List[dict]:
    try:
        result = []
        
        # Pre-fetch specifications if code_id is provided
        code_specs = {}
        if code_id:
            specs = db.query(CodeTestParameterSpecification).filter(
                CodeTestParameterSpecification.code_id == code_id
            ).all()
            code_specs = {s.question_id: s.specification for s in specs}

        for t in tests:
            # Validate and convert to dict
            test_data = CatalogTestOut.model_validate(t, from_attributes=True).model_dump()
            
            # Enrich with content from linked chapter if available
            if t.chapter_relation and t.chapter_relation.content:
                test_data['instructions'] = t.chapter_relation.content
            
            # Override specifications if code-specific ones exist
            if 'questions' in test_data:
                for q in test_data['questions']:
                    q_id = UUID(str(q['id'])) if isinstance(q['id'], str) else q['id']
                    if q_id in code_specs:
                        q['specification'] = code_specs[q_id]
                
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
