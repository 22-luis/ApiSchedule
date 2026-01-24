import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.modules.quality.services.find_chapters import find_chapters
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.qc_manual import QcManual
from app.modules.quality.schemas.qc_manual import QcManualCreate, QcManualOut, SectionOut, Chapters, HierarchyOut

from app.modules.quality.services.Split_sections import split_html_into_sections
from app.modules.core.models.role import UserRole
from app.shared.utils.core.dependencies import require_roles

router = APIRouter(prefix="/manual", tags=["manual"])

@router.post("/", response_model=QcManualOut, status_code=201)
def create_qc_manual(
    manual_data: QcManualCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        # Check if we already have structured content with sections (from updated frontend)
        final_content = manual_data.content
        
        # Determine if we need to re-split
        # If 'sections' key is missing or empty, we assume legacy or raw HTML input
        needs_split = True
        
        if isinstance(final_content, dict):
            if "capitulos" in final_content:
                # Handle new hierarchical format (Spanish keys)
                # We need to map it to the internal 'hierarchy' format (English keys)
                
                def map_node(node_data):
                    # Extract basic info
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
                            if block_val:
                                text_content_parts.append(block_val)
                        
                        elif block_type == "sub_capitulo":
                            sub_node = map_node(block)
                            node["sub_chapters"].append(sub_node)
                            
                        elif block_type == "prueba":
                            test_node = {
                                "id": str(block.get("id", "")),
                                "title": block.get("titulo", ""),
                                "content": block_val,
                            }
                            if "descripcion" in block:
                                test_node["content"] = f"<p><strong>{block.get('descripcion')}</strong></p>{test_node['content']}"
                                
                            node["tests"].append(test_node)
                    
                    node["content"] = "".join(text_content_parts)
                    return node

                mapped_hierarchy = [map_node(chapter) for chapter in final_content["capitulos"]]
                
                # Update final_content to stored format
                final_content = {
                    "hierarchy": mapped_hierarchy,
                    "sections": [] # Legacy support if needed, but keeping empty for now
                }
                needs_split = False # Already structured

            elif "sections" in final_content and final_content["sections"]:
                # Frontend sent structural metadata (Legacy or different format), trust it
                # We still might want to ensure 'content_html' is there or updated, 
                # but 'sections' dict is key.
                needs_split = False
            elif "content_html" in final_content:
                # Use content_html for splitting
                content_to_split = final_content["content_html"]
            else:
                 # Fallback, treat entire dict or string as content?
                 # If it's a dict without content_html, we can't easily split it unless we concatenate values.
                 # Let's assume manual_data.content is what we split if not a dict with 'content_html'
                 content_to_split = final_content
        else:
            content_to_split = final_content

        if needs_split:
            # Procesar el HTML para dividirlo en secciones
            # Note: split_html_into_sections returns a Dict[str, str], NO valid 'sections' metadata list.
            sections = split_html_into_sections(content_to_split)
            final_content = sections
        
        new_manual = QcManual(
            name=manual_data.name,
            content=final_content,
            version=0,
            created_by=current_user.username
        )
        db.add(new_manual)
        db.flush()
        new_manual.version = new_manual.id
        db.commit()
        db.refresh(new_manual)
        return new_manual
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chapters", response_model=Chapters, description="Devuelve una lista de secciones del manual")
def get_chapters(
        db: Session = Depends(get_db),
        _current_user = Depends(get_current_user)
):
    query = db.query(QcManual)
    
    # Optional filtering by name (logic for chapters usually implies a specific manual context)
    # If no name provided, we can assume the oldest "unnamed" one or the very latest across all.
    # But usually this is called in context of a specific manual.
    manual = query.order_by(QcManual.id.desc()).first()

    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")

    chapters = find_chapters(manual.content)

    return {
        "manual_id": manual.id,
        "chapters": chapters
    }

@router.get("/list", response_model=list[str])
def list_manual_names(
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    """
    Returns a list of unique manual names.
    """
    names = db.query(QcManual.name).distinct().all()
    # names is a list of tuples like [('Manual 1',), (None,)]
    # Filter out None and return flat list
    return [n[0] for n in names if n[0] is not None]



@router.get("/hierarchy", response_model=HierarchyOut)
def get_manual_hierarchy(
    name: str | None = None,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    query = db.query(QcManual)
    if name:
        query = query.filter(QcManual.name == name)
        
    manual = query.order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    
    # Check if 'hierarchy' key exists (from migration)
    hierarchy = []
    if isinstance(manual.content, dict) and "hierarchy" in manual.content:
        hierarchy = manual.content["hierarchy"]
    
    return {
        "manual_id": manual.id,
        "name": manual.name,
        "hierarchy": hierarchy
    }



@router.get("/section/{section_name}", response_model=SectionOut)
def get_section(
    section_name: str,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    # Traemos el último registro (versión más reciente)
    manual = db.query(QcManual).order_by(QcManual.id.desc()).first()
    
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    
    # 1. Intento de búsqueda exacta en estructura antigua (diccionario plano)
    section_content = None
    manual_content = manual.content
    
    # Check for new structure: 'sections' list
    if isinstance(manual_content, dict) and "sections" in manual_content and isinstance(manual_content["sections"], list):
        sections_list = manual_content["sections"]
        
        # Helper for slugify available to both paths
        def slugify(text):
            if not text: return ""
            text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
            text = re.sub(r'[^\w\s-]', '', text).strip().lower()
            return re.sub(r'[-\s]+', '-', text)

        target_slug = slugify(section_name)
        clean_target_slug = re.sub(r'^section-\d+-', '', target_slug)

        # Map header levels to integers for comparison
        level_map = {'h1': 1, 'h2': 2, 'h3': 3, 'h4': 4, 'h5': 5, 'h6': 6}

        match_index = -1
        
        # 1. Find the matching section index
        for i, section in enumerate(sections_list):
            title = section.get('title', '')
            title_slug = slugify(title)
            sec_id = section.get('id', '')
            
            if (section_name == title or 
                section_name == sec_id or 
                target_slug == title_slug or 
                clean_target_slug in title_slug):
                match_index = i
                break
        
        # 2. If found, aggregate content
        if match_index != -1:
            start_section = sections_list[match_index]
            start_level_str = start_section.get('level', 'h10') # Default to high number if unknown
            start_level = level_map.get(start_level_str, 99)
            
            aggregated_content = []
            
            # Add content of the matched section itself
            # We assume the main title is displayed by the frontend, so we don't add the H tag for the start section
            # unless it's missing content and we want to be safe, but typically frontend shows title.
            # However, if the start section *has* content (intro text), add it.
            if "content" in start_section:
                aggregated_content.append(start_section["content"])
            elif "content_html" in start_section:
                aggregated_content.append(start_section["content_html"])
            
            # Iterate through subsequent sections
            for j in range(match_index + 1, len(sections_list)):
                current_section = sections_list[j]
                current_level_str = current_section.get('level', 'h1')
                current_level = level_map.get(current_level_str, 1)
                
                # Stop if we hit a sibling or parent (same level or higher up the hierarchy / lower number)
                # e.g. if start is H1(1), stop at next H1(1). 
                # e.g. if start is H2(2), stop at next H2(2) or H1(1).
                if current_level <= start_level:
                    break
                
                # It is a child (sub-section). Render its title and content.
                title = current_section.get('title', '')
                content = current_section.get('content_html') or current_section.get('content', '')
                
                # Append formatted HTML with semantic structure
                # Use Tailwind classes directly or custom classes
                
                bg_color = ""
                border_color = ""
                header_color = ""
                padding = "p-4"
                margin = "mb-6"
                rounded = "rounded-lg"
                
                if current_level == 1: # Chapter (H1)
                    bg_color = "bg-white"
                    border_color = "border-l-4 border-blue-600"
                    header_class = "text-2xl font-bold text-gray-900 border-b pb-2 mb-3"
                    container_class = f"{bg_color} {border_color} shadow-sm {padding} {margin} {rounded}"
                
                elif current_level == 2: # Sub-chapter (H2)
                    bg_color = "bg-blue-50/50"
                    border_color = "border-l-4 border-blue-400"
                    header_class = "text-xl font-semibold text-blue-800 mb-2"
                    container_class = f"{bg_color} {border_color} {padding} {margin} {rounded}"
                
                elif current_level == 3: # Test (H3)
                    bg_color = "bg-white"
                    border_color = "border border-gray-100"
                    header_class = "text-lg font-medium text-gray-800 flex items-center gap-2"
                    # Add a badge or icon indicator for Test
                    badge = '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">Prueba</span>'
                    title = f"{badge} {title}"
                    container_class = f"{bg_color} {border_color} shadow-sm {padding} mb-4 {rounded} ml-4"
                else: 
                     container_class = "pl-4 border-l-2 border-gray-200 mb-4"
                     header_class = "font-medium text-gray-700"

                section_html = f"""
                <div class="{container_class}">
                    <{current_level_str} class="{header_class}">{title}</{current_level_str}>
                    <div class="prose prose-sm max-w-none text-gray-600">
                        {content}
                    </div>
                </div>
                """
                
                aggregated_content.append(section_html)
            
            section_content = "\n".join(aggregated_content)
                
    # Fallback to legacy dictionary lookup if not found yet
    if section_content is None:
        # 1. Direct lookup
        section_content = manual.content.get(section_name)
    
        # 2. Si falla, intento de búsqueda normalizada (slug/insensible a mayúsculas)
        if section_content is None:
            
            def slugify(text):
                text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
                text = re.sub(r'[^\w\s-]', '', text).strip().lower()
                return re.sub(r'[-\s]+', '-', text)

            target_slug = slugify(section_name)
            
            clean_target_slug = re.sub(r'^section-\d+-', '', target_slug)

            if isinstance(manual.content, dict):
                for key, value in manual.content.items():
                    # Skip non-content keys if they exist at top level and weren't caught above
                    if key in ["General", "content_html", "sections"]: 
                        continue
                        
                    key_slug = slugify(key)
                    if key_slug == target_slug or key_slug == clean_target_slug or key_slug in clean_target_slug:
                        section_content = value
                        break
    
    if section_content is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Sección '{section_name}' no encontrada."
        )
    
    return {
        "section_name": section_name,
        "content": section_content
    }

@router.get("/latest", 
             response_model=QcManualOut, 
             dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))])
def get_latest_qc_manual(name: str | None = None, db: Session = Depends(get_db)):
    query = db.query(QcManual)
    if name:
        query = query.filter(QcManual.name == name)
    manual = query.order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    return manual

@router.delete("/{name}", status_code=204)
def delete_qc_manual(
    name: str,
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR))
):
    """
    Deletes all records of a manual by its name.
    """
    manuals = db.query(QcManual).filter(QcManual.name == name).all()
    if not manuals:
        raise HTTPException(status_code=404, detail="Manual no encontrado")
        
    for m in manuals:
        db.delete(m)
    
    db.commit()
    return None
