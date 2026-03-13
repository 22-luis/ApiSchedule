import logging
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.codes.models.preparation import Preparation
from app.modules.codes.repositories import preparation_repository
from app.modules.codes.schemas.preparation import PreparationCreate, PreparationOut
from app.shared.utils.business.data_cleaning import clean_int, clean_str

logger = logging.getLogger(__name__)


def create_preparation(db: Session, preparation_data: PreparationCreate) -> Preparation:
    """Crea una nueva preparación en la base de datos."""
    db_preparation = Preparation(**preparation_data.model_dump())
    return preparation_repository.save(db, db_preparation)


def get_preparations(db: Session) -> List[PreparationOut]:
    """Devuelve todas las preparaciones."""
    preparations = preparation_repository.find_all(db)
    return [PreparationOut.model_validate(p) for p in preparations]


def get_preparation_by_id(db: Session, preparation_id: str) -> Preparation:
    """Obtiene una preparación por ID. Lanza 404 si no existe."""
    preparation = preparation_repository.find_by_id(db, preparation_id)
    if not preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    return preparation


def update_preparation(
    db: Session, preparation_id: str, preparation_update: PreparationCreate
) -> Preparation:
    """Actualiza una preparación existente."""
    db_preparation = preparation_repository.find_by_id(db, preparation_id)
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    
    for field, value in preparation_update.model_dump(exclude_unset=True).items():
        setattr(db_preparation, field, value)
    
    preparation_repository.commit(db)
    db.refresh(db_preparation)
    return db_preparation


def delete_preparation(db: Session, preparation_id: str) -> dict:
    """Elimina una preparación de la base de datos."""
    db_preparation = preparation_repository.find_by_id(db, preparation_id)
    if not db_preparation:
        raise HTTPException(status_code=404, detail="Preparation not found")
    
    preparation_repository.delete(db, db_preparation)
    preparation_repository.commit(db)
    return {"message": "Preparation deleted successfully"}


def bulk_upload_preparations(db: Session, preparations: list) -> dict:
    """
    Sincronización masiva de preparaciones desde un Excel.
    """
    all_db_preps = preparation_repository.find_all(db)
    existing_preps_map = {clean_str(p.description): p for p in all_db_preps}
    existing_ids_map = {str(p.id): p for p in all_db_preps}

    created, updated, deleted, errors = 0, 0, 0, []
    processed_ids: set = set()
    sync_mode = any(prep.get("id") for prep in preparations)

    for idx, prep_data in enumerate(preparations):
        prep_id = prep_data.get("id")
        description = clean_str(prep_data.get("description"))
        minutes = clean_int(prep_data.get("minutes"))

        if not description or minutes is None:
            errors.append({"row": idx + 1, "error": "Falta descripción o minutos"})
            continue

        existing_prep = None
        if prep_id and str(prep_id) in existing_ids_map:
            existing_prep = existing_ids_map[str(prep_id)]
        else:
            existing_prep = existing_preps_map.get(description)

        if existing_prep:
            has_changes = False
            new_mins = clean_int(minutes)

            if clean_str(existing_prep.description) != description:
                existing_code_desc = clean_str(existing_prep.description)
                existing_prep.description = description
                has_changes = True

            if clean_int(existing_prep.minutes) != new_mins:
                existing_prep.minutes = new_mins
                has_changes = True

            if has_changes:
                updated += 1
                logger.debug(f"Preparación {existing_prep.description} (ID: {existing_prep.id}) actualizada.")
            processed_ids.add(existing_prep.id)
        else:
            db_prep = Preparation(description=description, minutes=minutes)
            preparation_repository.save(db, db_prep, flush=True)
            created += 1
            processed_ids.add(db_prep.id)
            existing_preps_map[description] = db_prep
            existing_ids_map[str(db_prep.id)] = db_prep
            logger.debug(f"Nueva preparación creada: {db_prep.description} (ID: {db_prep.id})")

    if sync_mode:
        preps_to_delete = [p for p in all_db_preps if p.id not in processed_ids]
        for p in preps_to_delete:
            logger.info(f"Sincronización: Eliminando preparación {p.description} (ID: {p.id})")
            preparation_repository.delete(db, p)
            deleted += 1

    if created > 0 or updated > 0 or deleted > 0:
        preparation_repository.commit(db)

    total_processed = len(preparations) - len(errors)
    unchanged = total_processed - created - updated

    logger.info(
        f"Carga de preparaciones completada - Creadas: {created}, Actualizadas: {updated}, "
        f"Eliminadas: {deleted}, Sin cambios: {unchanged}"
    )

    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "unchanged": unchanged,
        "errors": errors,
        "total_processed": total_processed,
    }
