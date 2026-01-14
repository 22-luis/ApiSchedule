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

router = APIRouter(prefix="/codes/{code_id}/tests", tags=["codes"])

@router.post("/",   
             response_model=List[CodeTestOut], 
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def link_tests_to_code(
    code_id: UUID, 
    link_data: CodeTestLink, 
    db: Session = Depends(get_db)
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

@router.get("/",   
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
    # Obtener el último manual
    manual = db.query(QcManual).order_by(QcManual.id.desc()).first()
    if not manual or not manual.content:
        return [CatalogTestOut.model_validate(t, from_attributes=True).model_dump() for t in tests]

    content_dict = manual.content
    # Pre-calcular slugs del manual para eficiencia
    slug_map = {slugify(k): v for k, v in content_dict.items()}

    result = []
    for t in tests:
        test_data = CatalogTestOut.model_validate(t).model_dump()
        # manual_section_id has been removed from CatalogTest model in recent migrations
        # if t.manual_section_id:
        #     # Intentar búsqueda exacta
        #     content = content_dict.get(t.manual_section_id)
        #     
        #     # Si falla, intentar búsqueda normalizada
        #     if content is None:
        #         target_slug = slugify(t.manual_section_id)
        #         clean_target_slug = re.sub(r'^section-\d+-', '', target_slug)
        #         
        #         content = slug_map.get(target_slug) or slug_map.get(clean_target_slug)
        #         
        #         # Búsqueda por subcadena si aún no hay nada
        #         if content is None:
        #             for s_slug, s_content in slug_map.items():
        #                 if s_slug in clean_target_slug or clean_target_slug in s_slug:
        #                     content = s_content
        #                     break
        #     
        #     test_data["manual_content"] = content
        result.append(test_data)
    
    return result

@router.delete("/{test_id}", 
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
