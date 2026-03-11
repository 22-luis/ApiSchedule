from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.modules.codes.models.preparation import Preparation
from app.modules.codes.schemas.preparation import PreparationCreate, PreparationOut
from app.shared.db.session import get_db
from app.modules.organization.models.user import User
from app.shared.utils.core.dependencies import require_roles
from app.modules.organization.models.role import UserRole
from app.shared.utils.business.data_cleaning import clean_int, clean_str

router = APIRouter(prefix="/preparations", tags=["preparations"])

@router.post("/", response_model=PreparationOut)
def create_preparation(
    preparation: PreparationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_preparation = Preparation(**preparation.model_dump())
    db.add(db_preparation)
    db.commit()
    db.refresh(db_preparation)
    return db_preparation

@router.post("/bulk_upload")
def bulk_upload_preparations(preparations: list[dict], db: Session = Depends(get_db), _current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    all_db_preps = db.query(Preparation).all()
    existing_preps_map = {clean_str(p.description): p for p in all_db_preps}
    existing_ids_map = {str(p.id): p for p in all_db_preps}
    
    created, updated, deleted, errors = 0, 0, 0, []
    processed_ids = set()
    sync_mode = any(prep.get("id") for prep in preparations)
    
    for idx, prep_data in enumerate(preparations):
        prep_id = prep_data.get("id")
        description = clean_str(prep_data.get("description"))
        minutes = clean_int(prep_data.get("minutes"))
        
        if not description or minutes is None:
            errors.append({"row": idx+1, "error": "Falta descripción o minutos"})
            continue
        
        # Buscar si existe la preparación
        existing_prep = None
        if prep_id and str(prep_id) in existing_ids_map:
            existing_prep = existing_ids_map[str(prep_id)]
        else:
            existing_prep = existing_preps_map.get(description)
        
        if existing_prep:
            # Si existe, actualizar si hay cambios
            has_changes = False
            # description ya viene limpia (uppercase) de arriba
            new_mins = clean_int(minutes)
            
            if clean_str(existing_prep.description) != description:
                existing_prep.description = description
                has_changes = True
            
            if clean_int(existing_prep.minutes) != new_mins:
                existing_prep.minutes = new_mins
                has_changes = True
            
            if has_changes:
                updated += 1
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Preparación {existing_prep.description} (ID: {existing_prep.id}) actualizada.")
            processed_ids.add(existing_prep.id)
        else:
            # Si no existe, crear nueva
            db_prep = Preparation(
                description=description,
                minutes=minutes
            )
            db.add(db_prep)
            db.flush() # Para obtener el ID
            created += 1
            processed_ids.add(db_prep.id)
            # Actualizar mapas para evitar duplicados en la misma carga
            existing_preps_map[description] = db_prep
            existing_ids_map[str(db_prep.id)] = db_prep
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Nueva preparación creada: {db_prep.description} (ID: {db_prep.id})")
    
    # Sincronización: Eliminar si estamos en modo sync
    if sync_mode:
        preps_to_delete = [p for p in all_db_preps if p.id not in processed_ids]
        for p in preps_to_delete:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Sincronización: Eliminando preparación {p.description} (ID: {p.id})")
            db.delete(p)
            deleted += 1
    
    if created > 0 or updated > 0 or deleted > 0:
        db.commit()
    
    total_processed = len(preparations) - len(errors)
    unchanged = total_processed - created - updated
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Carga de preparaciones completada - Creadas: {created}, Actualizadas: {updated}, Eliminadas: {deleted}, Sin cambios: {unchanged}")
    
    return {
        "created": created, 
        "updated": updated, 
        "deleted": deleted,
        "unchanged": unchanged,
        "errors": errors,
        "total_processed": total_processed
    }

@router.get("/", response_model=List[PreparationOut])
def get_preparations(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    preparations = db.query(Preparation).all()
    return [PreparationOut.model_validate(p) for p in preparations]

@router.get("/{preparation_id}", response_model=PreparationOut)
def get_preparation(
    preparation_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    preparation = db.query(Preparation).filter(Preparation.id == preparation_id).first()
    if not preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    return preparation

@router.patch("/{preparation_id}", response_model=PreparationOut)
def update_preparation(
    preparation_id: str,
    preparation_update: PreparationCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_preparation = db.query(Preparation).filter(Preparation.id == preparation_id).first()
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    for field, value in preparation_update.model_dump(exclude_unset=True).items():
        setattr(db_preparation, field, value)
    db.commit()
    db.refresh(db_preparation)
    return db_preparation

@router.delete("/{preparation_id}")
def delete_preparation(
    preparation_id: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    db_preparation = db.query(Preparation).filter(Preparation.id == preparation_id).first()
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    db.delete(db_preparation)
    db.commit()
    return {"message": "Preparation deleted successfully"}