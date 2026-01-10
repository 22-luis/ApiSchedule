import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.modules.quality.services.find_chapters import find_chapters
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.quality.models.qc_manual import QcManual
from app.modules.quality.schemas.qc_manual import QcManualCreate, QcManualOut, SectionOut, Chapters
from app.modules.quality.services.Split_sections import split_html_into_sections

router = APIRouter(prefix="/manual", tags=["manual"])

@router.post("/", response_model=QcManualOut, status_code=201)
def create_qc_manual(
    manual_data: QcManualCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    try:
        # Extraer el HTML si viene envuelto en un diccionario
        content_to_split = manual_data.content
        if isinstance(content_to_split, dict) and "content_html" in content_to_split:
            content_to_split = content_to_split["content_html"]

        # Procesar el HTML para dividirlo en secciones
        sections = split_html_into_sections(content_to_split)
        
        new_manual = QcManual(
            content=sections,
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
    manual = db.query(QcManual).order_by(QcManual.id.desc()).first()

    if not manual:
        raise HTTPException(status_code=404, detail="Manual no encontrado")

    chapters = find_chapters(manual.content)

    return {
        "manual_id": manual.id,
        "chapters": chapters
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
    
    # 1. Intento de búsqueda exacta
    section_content = manual.content.get(section_name)
    
    # 2. Si falla, intento de búsqueda normalizada (slug/insensible a mayúsculas)
    if section_content is None:
        
        def slugify(text):
            # Normalizar y quitar acentos
            text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
            # Quitar caracteres especiales, excepto guiones y espacios
            text = re.sub(r'[^\w\s-]', '', text).strip().lower()
            # Reemplazar espacios y guiones múltiples por uno solo
            return re.sub(r'[-\s]+', '-', text)

        target_slug = slugify(section_name)
        
        # Intentar limpiar prefijos comunes como 'section-1-', 'section-2-', etc.
        # Esto ayuda si el frontend envía un ID generado automáticamente
        clean_target_slug = re.sub(r'^section-\d+-', '', target_slug)

        for key, value in manual.content.items():
            key_slug = slugify(key)
            # Comparación por slug exacto o si el slug de la clave está contenido en el pedido
            if key_slug == target_slug or key_slug == clean_target_slug or key_slug in clean_target_slug:
                section_content = value
                break
    
    if section_content is None:
        raise HTTPException(
            status_code=404, 
            detail=f"Sección '{section_name}' no encontrada. Disponibles: {list(manual.content.keys())}"
        )
    
    return {
        "section_name": section_name,
        "content": section_content
    }

@router.get("/latest", response_model=QcManualOut)
def get_latest_qc_manual(db: Session = Depends(get_db)):
    manual = db.query(QcManual).order_by(QcManual.id.desc()).first()
    if not manual:
        raise HTTPException(status_code=404, detail="Manual QC no encontrado")
    return manual
