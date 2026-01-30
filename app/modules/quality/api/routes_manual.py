import re
import uuid
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.modules.quality.services.find_chapters import find_chapters
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.quality_manual import QualityManual
from app.modules.quality.models.qc_manual import QcManual
from app.modules.quality.models.qc_manual_chapter import QcManualChapter
from app.modules.quality.schemas.qc_manual import QcManualBase, QcManualCreate, QcManualOut, SectionOut, Chapters, HierarchyOut, QcManualWithChaptersOut
from app.modules.quality.schemas.qc_manual_chapter import (
    QcManualChapterCreate,
    QcManualChapterUpdate,
    QcManualChapterOut,
    QcManualChapterTree
)
from app.modules.quality.models.catalog_test import CatalogTest
from app.modules.quality.services import qc_manual_chapter_service
from app.modules.quality.services.Split_sections import split_html_into_sections
from app.modules.core.models.role import UserRole
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/manual", tags=["manual"])

@router.post("/identity", response_model=QcManualOut, status_code=201)
def create_manual_identity(
    manual_data: QcManualBase,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Creates only the manual identity (QualityManual) and an initial audit revision (QcManual)"""
    try:
        # 1. Get or Create the Master Manual record (QualityManual)
        qm = db.query(QualityManual).filter(QualityManual.name == manual_data.name).first()
        if qm:
            raise HTTPException(status_code=400, detail="Ya existe un instructivo con ese nombre")
            
        qm = QualityManual(
            name=manual_data.name,
            created_by=current_user.username
        )
        db.add(qm)
        db.flush()
        
        # 2. Create the initial Audit/Link record (QcManual)
        new_audit = QcManual(
            quality_manual_id=qm.id,
            created_by=current_user.username
        )
        db.add(new_audit)
        db.commit()
        db.refresh(new_audit)
        
        new_audit.name = qm.name 
        return new_audit
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=QcManualOut, status_code=201)
def create_qc_manual(
    manual_data: QcManualCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        # 1. Get or Create the Master Manual record (QualityManual)
        qm = db.query(QualityManual).filter(QualityManual.name == manual_data.name).first()
        if not qm:
            qm = QualityManual(
                name=manual_data.name,
                created_by=current_user.username
            )
            db.add(qm)
            db.flush()
        
        # 2. Check for latest revision to UPDATE instead of creating new
        latest_audit = db.query(QcManual).filter(QcManual.quality_manual_id == qm.id).order_by(QcManual.id.desc()).first()
        
        target_audit = None
        is_update = False
        
        if latest_audit:
            # UPDATE EXISTING
            target_audit = latest_audit
            is_update = True
            # We could update updated_by if we had the field, but we assume chapter updates track this.
        else:
            # CREATE NEW
            target_audit = QcManual(
                quality_manual_id=qm.id,
                created_by=current_user.username
            )
            db.add(target_audit)
            db.flush()
        
        # 3. Process Content and Create/Sync Chapters
        final_content = manual_data.content
        needs_split = True
        
        if isinstance(final_content, dict):
            if "capitulos" in final_content or "hierarchy" in final_content:
                needs_split = False
            
            if "capitulos" in final_content and not "hierarchy" in final_content:
                def map_node(node_data):
                    node = {
                        "id": str(node_data.get("id", "")),
                        "title": node_data.get("titulo", ""),
                        "content": "",
                        "sub_chapters": [],
                        "tests": [] 
                    }
                    raw_content_list = node_data.get("contenido", [])
                    text_content_parts = []
                    for block in raw_content_list:
                        block_type = block.get("tipo", "texto")
                        block_val = block.get("valor", "")
                        if block_type == "texto":
                            if block_val: text_content_parts.append(block_val)
                        elif block_type == "sub_capitulo":
                            node["sub_chapters"].append(map_node(block))
                        elif block_type == "prueba":
                            test_node = {"id": str(block.get("id", "")), "title": block.get("titulo", ""), "content": block_val}
                            if "descripcion" in block:
                                test_node["content"] = f"<p><strong>{block.get('descripcion')}</strong></p>{test_node['content']}"
                            node["tests"].append(test_node)
                    node["content"] = "".join(text_content_parts)
                    return node

                final_content = {
                    "hierarchy": [map_node(chapter) for chapter in final_content["capitulos"]],
                }

            elif "content_html" in final_content:
                content_to_split = final_content["content_html"]

        if needs_split:
            # Note: We still use split_html_into_sections for legacy/raw HTML
            # but we won't store the result in QcManual, only use it to create chapters
            sections = split_html_into_sections(content_to_split)
            # Convert split sections to flat hierarchy for creation
            hierarchy = []
            for title, html in sections.items():
                hierarchy.append({"title": title, "content": html, "sub_chapters": [], "tests": []})
            final_content = {"hierarchy": hierarchy}
        
        # 4. Create or Sync chapters
        if isinstance(final_content, dict) and "hierarchy" in final_content:
            if is_update:
                qc_manual_chapter_service.sync_chapters_from_hierarchy(
                    db, target_audit.id, final_content["hierarchy"], current_user.username
                )
            else:
                qc_manual_chapter_service.create_chapters_from_hierarchy(
                    db, target_audit.id, final_content["hierarchy"], current_user.username
                )
        
        db.flush()

        # --- SAFEGUARD: If no chapters were created, do not create a new empty revision ---
        count_chapters = db.query(QcManualChapter).filter(QcManualChapter.manual_id == target_audit.id).count()
        
        if count_chapters == 0:
             # Check if previous revision exists for this manual name (QualityManual)
             prev_count = db.query(QcManual).filter(QcManual.quality_manual_id == qm.id).count()
             
             if prev_count > 1 and not is_update:
                 # Only rollback if we created a NEW empty revision. 
                 # If we updated and deleted everything, maybe that's intentional? 
                 # But safer to block partial updates that wipe manual.
                 db.rollback()
                 raise HTTPException(status_code=400, detail="Error: El instructivo está vacío. No se guardó.")
             elif is_update and prev_count > 0:
                  # If updating, 0 chapters means we deleted all.
                  # Let's prevent total wipeout for safety unless force?
                  pass

        migrate_catalog_tests_to_new_manual(db, target_audit.id)
        db.commit()
        db.refresh(target_audit)
        
        # Return the audit record
        target_audit.name = qm.name 
        return target_audit
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

def migrate_catalog_tests_to_new_manual(db: Session, new_manual_id: int):
    """
    Finds existing catalog tests and attempts to link them to the chapters 
    of the new manual version based on titles and hierarchical paths.
    """
    # 1. Get all current chapters for the new manual
    new_chapters = db.query(QcManualChapter).filter(QcManualChapter.manual_id == new_manual_id).all()
    if not new_chapters:
        return

    # Map for easy lookup by (title, chapter_type, order)
    # We use a tuple of (title, type) as a basic heuristic
    # A better heuristic would be the full hierarchical path, but let's start with title+type
    chapter_map = {(c.title, c.chapter_type): c.id for c in new_chapters}

    # 2. Get all CatalogTests
    tests = db.query(CatalogTest).all()
    
    for test in tests:
        # Try to find a matching chapter in the new manual
        # If it was already linked to a chapter, try to find a chapter with same title in new manual
        match_found = False
        
        if test.chapter_id:
            old_chapter = db.query(QcManualChapter).filter(QcManualChapter.id == test.chapter_id).first()
            if old_chapter:
                # Look for a chapter with same title and type in the NEW manual
                new_chapter_id = chapter_map.get((old_chapter.title, old_chapter.chapter_type))
                if new_chapter_id:
                    test.chapter_id = new_chapter_id
                    match_found = True
        
        if not match_found and test.chapter:
            # Fallback for legacy 'chapter' string linkage
            # Try to match it to a 'chapter' type chapter in the new manual
            new_chapter_id = chapter_map.get((test.chapter, 'chapter'))
            if new_chapter_id:
                test.chapter_id = new_chapter_id
                match_found = True
            else:
                # Try 'sub_chapter' or 'test' too if name matches
                for (title, ctype), cid in chapter_map.items():
                    if title == test.chapter:
                        test.chapter_id = cid
                        match_found = True
                        break

@router.get("/chapters", response_model=Chapters)
def get_chapters(
        name: str | None = None,
        db: Session = Depends(get_db),
        _current_user = Depends(get_current_user)
):
    """Get latest chapters for a manual by its master name"""
    # Join QcManual with QualityManual to find the latest revision for this name
    query = db.query(QcManual).join(QualityManual).filter(QualityManual.name == name) if name else db.query(QcManual).join(QualityManual)
    
    manual = query.order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")

    # Get root chapters from relational structure
    chapter_records = db.query(QcManualChapter).filter(
        QcManualChapter.manual_id == manual.id,
        QcManualChapter.parent_chapter_id.is_(None)
    ).order_by(QcManualChapter.order).all()
    
    chapters = [ch.title for ch in chapter_records]

    return {
        "manual_id": manual.id,
        "chapters": chapters
    }

@router.get("/list", response_model=list[str])
def list_manual_names(
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    """Returns a list of unique manual names from the identity table."""
    # Query QualityManual instead of QcManual
    names = db.query(QualityManual.name).all()
    return [n[0] for n in names]

@router.get("/identities", response_model=list[dict])
def get_identities(
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    """Returns a list of manual identities with ID and name."""
    manuals = db.query(QualityManual.id, QualityManual.name).all()
    return [{"id": m.id, "name": m.name} for m in manuals]



@router.get("/hierarchy", response_model=HierarchyOut)
def get_manual_hierarchy(
    name: str | None = None,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    # Join to find latest revision by name
    query = db.query(QcManual).join(QualityManual)
    if name:
        query = query.filter(QualityManual.name == name)
        
    manual = query.order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    
    # Fetch relational tree
    chapters = qc_manual_chapter_service.get_chapter_tree(db, manual.id)
    
    def map_to_hierarchy(ch):
        node = {
            "id": str(ch.id),
            "title": ch.title,
            "content": ch.content or "",
            "sub_chapters": [map_to_hierarchy(sc) for sc in ch.sub_chapters if sc.chapter_type != 'test'],
            "tests": [{"id": str(t.id), "title": t.title, "content": t.content or ""} 
                      for t in ch.sub_chapters if t.chapter_type == 'test']
        }
        return node

    hierarchy = [map_to_hierarchy(ch) for ch in chapters]
    
    return {
        "manual_id": manual.id,
        "name": manual.quality_manual.name, # Access from relationship
        "hierarchy": hierarchy
    }



@router.get("/section/{section_name}", response_model=SectionOut)
def get_section(
    section_name: str,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    is_uuid = False
    try:
        uuid_obj = uuid.UUID(section_name)
        is_uuid = True
    except ValueError:
        is_uuid = False

    chapter = None
    if is_uuid:
        # Search by ID (Globally Unique)
        chapter = db.query(QcManualChapter).filter(QcManualChapter.id == section_name).first()
    else:
        # Search by Title (Legacy) - Limited to latest revision of ANY manual (This logic was existing but potentially flawed if multiple manuals exist)
        # We preserve existing behavior for non-UUIDs.
        manual = db.query(QcManual).join(QualityManual).order_by(QcManual.id.desc()).first()
        if not manual:
            raise HTTPException(status_code=404, detail="Manual QC no encontrado")
        
        chapter = db.query(QcManualChapter).filter(
            QcManualChapter.manual_id == manual.id,
            QcManualChapter.title == section_name
        ).first()
    
    if chapter:
        aggregated_content = [chapter.content or ""]
        
        def get_all_sub_content(parent_id, level=2):
            subs = db.query(QcManualChapter).filter(QcManualChapter.parent_chapter_id == parent_id).order_by(QcManualChapter.order).all()
            parts = []
            for s in subs:
                tag = "h2" if s.chapter_type == "sub_chapter" else "h3"
                parts.append(f"<{tag}>{s.title}</{tag}>")
                if s.content:
                    parts.append(s.content)
                parts.extend(get_all_sub_content(s.id, level + 1))
            return parts

        aggregated_content.extend(get_all_sub_content(chapter.id))
        return {
            "section_name": section_name,
            "content": "\n".join(aggregated_content)
        }
    
    raise HTTPException(status_code=404, detail=f"Sección '{section_name}' no encontrada.")

@router.get("/{manual_id}/full-content", response_model=SectionOut)
def get_full_manual_content(
    manual_id: int,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    """
    Returns the aggregated content of ALL chapters for the latest revision 
    of the specified QualityManual (by ID).
    """
    # 1. Find latest audit for this Quality Manual ID
    latest_audit = db.query(QcManual).filter(QcManual.quality_manual_id == manual_id).order_by(QcManual.id.desc()).first()
    
    if not latest_audit:
        raise HTTPException(status_code=404, detail="Manual no encontrado")
        
    qm = db.query(QualityManual).filter(QualityManual.id == manual_id).first()
    manual_name = qm.name if qm else "Instructivo Completo"

    # 2. Helper to recursively build content
    def get_all_content_recursive(parent_id=None, level=1):
        # Fetch chapters at this level
        if parent_id is None:
             chapters = db.query(QcManualChapter).filter(
                 QcManualChapter.manual_id == latest_audit.id,
                 QcManualChapter.parent_chapter_id.is_(None)
             ).order_by(QcManualChapter.order).all()
        else:
             chapters = db.query(QcManualChapter).filter(
                 QcManualChapter.manual_id == latest_audit.id,
                 QcManualChapter.parent_chapter_id == parent_id
             ).order_by(QcManualChapter.order).all()
             
        parts = []
        for ch in chapters:
            # Skip tests in the full manual view usually, but user might want them? 
            # Request says "contenido de todos los capitulos associated al instructivo".
            # Let's include everything formatted nicely.
            
            # Determine Heading Level
            # Root = H1 (but inside manual usually H1 is title). Let's use H(level)
            tag = f"h{min(level, 6)}"
            parts.append(f"<{tag}>{ch.title}</{tag}>")
            
            if ch.content:
                parts.append(ch.content)
            
            # Recurse
            parts.extend(get_all_content_recursive(ch.id, level + 1))
            
        return parts

    # 3. Build Content
    full_content_parts = get_all_content_recursive(None, 1)
    
    return {
        "section_name": manual_name,
        "content": "\n<hr/>\n".join(full_content_parts) # Separate major blocks with spacing/lines if needed, or just standard flow
    }

@router.get("/latest", 
             response_model=QcManualOut, 
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def get_latest_qc_manual(name: str | None = None, db: Session = Depends(get_db)):
    # Join to find latest revision
    query = db.query(QcManual).join(QualityManual)
    if name:
        query = query.filter(QualityManual.name == name)
    manual = query.order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    
    # Synchronize name for schema output
    manual.name = manual.quality_manual.name
    return manual

@router.delete("/{name}", status_code=204)
def delete_qc_manual(
    name: str,
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR))
):
    """
    Deletes a manual identity and all its audit revisions (cascading).
    """
    qm = db.query(QualityManual).filter(QualityManual.name == name).first()
    if not qm:
        raise HTTPException(status_code=404, detail="Manual no encontrado")
        
    db.delete(qm)
    db.commit()
    return None


# ============================================================================
# NEW CHAPTER CRUD ENDPOINTS (Relational Structure)
# ============================================================================

@router.post("/{manual_id}/chapters", response_model=QcManualChapterOut, status_code=201)
def create_chapter(
    manual_id: int,
    chapter_data: QcManualChapterCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR))
):
    """Create a new chapter for a manual"""
    # Verify manual exists
    manual = db.query(QcManual).filter(QcManual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")
    
    # Verify parent chapter exists if specified
    if chapter_data.parent_chapter_id:
        parent = qc_manual_chapter_service.get_chapter_by_id(db, chapter_data.parent_chapter_id)
        if not parent or parent.manual_id != manual_id:
            raise HTTPException(status_code=404, detail="Parent chapter no encontrado")
    
    chapter = qc_manual_chapter_service.create_chapter(
        db, manual_id, chapter_data, current_user.username
    )
    return chapter


@router.patch("/chapters/{chapter_id}", response_model=QcManualChapterOut)
def update_chapter(
    chapter_id: uuid.UUID,
    chapter_data: QcManualChapterUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR))
):
    """Update a chapter"""
    chapter = qc_manual_chapter_service.update_chapter(
        db, chapter_id, chapter_data, current_user.username
    )
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter no encontrado")
    return chapter


@router.delete("/chapters/{chapter_id}", status_code=204)
def delete_chapter(
    chapter_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR))
):
    """Delete a chapter and its sub-chapters"""
    success = qc_manual_chapter_service.delete_chapter(db, chapter_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chapter no encontrado")
    return None


@router.get("/{manual_id}/chapters/tree", response_model=QcManualChapterTree)
def get_chapter_tree(
    manual_id: int,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    """Get full chapter hierarchy for a manual"""
    # Verify manual exists
    manual = db.query(QcManual).filter(QcManual.id == manual_id).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")
    
    chapters = qc_manual_chapter_service.get_chapter_tree(db, manual_id)
    return {
        "manual_id": manual_id,
        "chapters": chapters
    }
