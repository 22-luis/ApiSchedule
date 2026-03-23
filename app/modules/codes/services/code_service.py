import logging
import uuid
from typing import List, Optional

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.modules.codes.models.code import Code
from app.modules.codes.repositories import code_repository
from app.modules.codes.schemas.code import CodeCreate, CodeOut, CodePageOut, CodeUpdate
from app.modules.codes.schemas.code_bulk import CodeBulkItem
from app.shared.utils.business.data_cleaning import (
    clean_float, clean_int, clean_str, clean_str_preserve_case,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CRUD básico
# ---------------------------------------------------------------------------

def create_code(db: Session, code_data: CodeCreate) -> Code:
    """Crea un nuevo código en la base de datos."""
    db_code = Code(**code_data.model_dump())
    return code_repository.save(db, db_code)


def get_codes(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> CodePageOut:
    """Lista paginada de códigos con búsqueda opcional."""
    codes, total = code_repository.find_all(db, skip=skip, limit=limit, search=search)
    return CodePageOut(codes=[CodeOut.model_validate(c) for c in codes], total=total)


def get_production_codes(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
) -> CodePageOut:
    """Lista paginada de códigos productivos con sus pruebas vinculadas."""
    codes, total = code_repository.find_production_codes(db, skip=skip, limit=limit, search=search)

    # Cargar pruebas vinculadas
    code_ids = [c.id for c in codes]
    rows = code_repository.find_tests_for_codes(db, code_ids)
    tests_map: dict = {}
    for code_id, test in rows:
        tests_map.setdefault(code_id, []).append(test)
    for c in codes:
        setattr(c, "tests", tests_map.get(c.id, []))

    return CodePageOut(codes=[CodeOut.model_validate(c) for c in codes], total=total)


def get_code_by_id(db: Session, code_id: uuid.UUID) -> Code:
    """Obtiene un código por su UUID. Lanza 404 si no existe."""
    code = code_repository.find_by_id(db, code_id)
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    return code


def update_code(db: Session, code_id: uuid.UUID, code_update: CodeUpdate) -> Code:
    """Actualiza los campos de un código existente."""
    db_code = code_repository.find_by_id(db, code_id)
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")

    for field, value in code_update.model_dump(exclude_unset=True).items():
        setattr(db_code, field, value)

    code_repository.commit(db)
    db.refresh(db_code)
    return db_code


def delete_code(db: Session, code_id: uuid.UUID) -> dict:
    """Elimina un código de la base de datos."""
    db_code = code_repository.find_by_id(db, code_id)
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    code_repository.delete(db, db_code)
    code_repository.commit(db)
    return {"message": "Code deleted successfully"}


# ---------------------------------------------------------------------------
# Búsquedas específicas
# ---------------------------------------------------------------------------

def get_code_by_code_and_activity(db: Session, code: str, activity: str) -> Code:
    """Busca un código por el par (code, activity). Lanza 404 si no existe."""
    code_obj = code_repository.find_by_code_and_activity(db, code, activity)
    if not code_obj:
        raise HTTPException(
            status_code=404,
            detail="Code not found with given code and activity",
        )
    return code_obj


def get_activity_details(db: Session, code: str, activity: str) -> dict:
    """Devuelve detalles de actividad para un par (code, activity). Empaqueta la respuesta."""
    logger.debug(f"Buscando detalles para código '{code}' y actividad '{activity}'")
    code_obj = code_repository.find_by_code_and_activity(db, code, activity)
    if not code_obj:
        logger.warning(f"No se encontró código '{code}' con actividad '{activity}'")
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró código '{code}' con actividad '{activity}'",
        )
    return {
        "success": True,
        "code": code,
        "activity": activity,
        "activity_details": code_obj,
        "message": f"Datos obtenidos exitosamente para código '{code}' y actividad '{activity}'",
    }


def get_code_activities(db: Session, code: str) -> dict:
    """Devuelve todas las actividades asociadas a un código."""
    code_objs = code_repository.find_by_code(db, code)
    if not code_objs:
        raise HTTPException(status_code=404, detail="Code not found")
    return {
        "code": code,
        "activities": code_objs,
        "total_activities": len(code_objs),
    }


def get_lotes_by_code(db: Session, code: str) -> dict:
    """Devuelve los lotes de órdenes activas para un código."""
    lotes = code_repository.find_lotes_by_code(db, code)
    return {"code": code, "lotes": lotes}


# ---------------------------------------------------------------------------
# Carga masiva
# ---------------------------------------------------------------------------

def bulk_upload_codes(db: Session, codes: List[dict]) -> dict:
    """
    Sincronización masiva de códigos desde un Excel.

    - Si algún registro incluye 'id', activa el modo sync (elimina los que no estén en el Excel).
    - Crea registros nuevos, actualiza los existentes si hay cambios.
    """
    logger.info(f"Iniciando carga masiva con {len(codes)} registros")

    all_db_codes = code_repository.find_all_no_filter(db)
    existing_codes_map = {
        (clean_str(c.code), clean_str(c.activity)): c for c in all_db_codes
    }
    existing_ids_map = {c.id: c for c in all_db_codes}
    logger.info(f"Se cargaron {len(existing_codes_map)} códigos existentes en memoria.")

    created, updated, deleted, errors = 0, 0, 0, []
    processed_ids: set = set()
    sync_mode = any(item.get("id") for item in codes)

    for idx, item_data in enumerate(codes):
        try:
            item = CodeBulkItem.model_validate(item_data)
        except ValidationError as e:
            errors.append({"row": idx + 2, "error": e.errors()})
            continue

        code_data = item.model_dump(exclude_unset=True)
        code_str = code_data.get("code")
        item_id = code_data.get("id")

        if not code_str:
            errors.append({"row": idx + 2, "error": "Fila sin código"})
            continue

        activity_str = code_data.get("activity")
        lookup_key = (clean_str(code_str), clean_str(activity_str))

        existing_code = None
        if item_id and item_id in existing_ids_map:
            existing_code = existing_ids_map[item_id]
        else:
            existing_code = existing_codes_map.get(lookup_key)

        useful_life = code_data.get("usefulLife") or code_data.get("usefullife")
        fabrication_code = code_data.get("fabricationCode") or code_data.get("fabricationc")

        if existing_code:
            new_values = {
                "description": code_data.get("description"),
                "unit": code_data.get("unit"),
                "type": code_data.get("type"),
                "quantity": code_data.get("quantity"),
                "time": code_data.get("time"),
                "people": code_data.get("people"),
                "performance": code_data.get("performance"),
                "material": code_data.get("material"),
                "presentation": code_data.get("presentation"),
                "fabricationCode": fabrication_code,
                "usefulLife": useful_life,
            }
            if item_id:
                new_values["code"] = code_data.get("code")
                new_values["activity"] = code_data.get("activity")

            has_changes = _apply_changes(existing_code, new_values)
            if has_changes:
                updated += 1
                logger.debug(f"Código {existing_code.code} (ID: {existing_code.id}) actualizado.")
            processed_ids.add(existing_code.id)
        else:
            new_code = _build_code(code_str, activity_str, code_data, useful_life, fabrication_code)
            code_repository.save(db, new_code, flush=True)
            created += 1
            processed_ids.add(new_code.id)
            existing_codes_map[lookup_key] = new_code
            existing_ids_map[new_code.id] = new_code
            logger.debug(f"Nuevo código creado: {new_code.code} (ID: {new_code.id})")

    # Sincronización: eliminar los que no vinieron en el Excel
    if sync_mode:
        for c in [c for c in all_db_codes if c.id not in processed_ids]:
            logger.info(f"Sincronización: Eliminando código {c.code} (ID: {c.id})")
            code_repository.delete(db, c)
            deleted += 1
        if deleted > 0:
            logger.info(f"Sincronización completa. Eliminados: {deleted}")

    if created > 0 or updated > 0 or deleted > 0:
        code_repository.commit(db)
        logger.info(f"Commit realizado. Creados: {created}, Actualizados: {updated}, Eliminados: {deleted}")

    total_processed = len(codes) - len(errors)
    unchanged = total_processed - created - updated

    logger.info(
        f"Carga masiva completada - Creados: {created}, Actualizados: {updated}, "
        f"Eliminados: {deleted}, Sin cambios: {unchanged}, Errores: {len(errors)}"
    )

    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "unchanged": unchanged,
        "errors": errors,
        "total_processed": total_processed,
    }


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _apply_changes(existing_code: Code, new_values: dict) -> bool:
    """Compara y aplica cambios campo a campo. Devuelve True si hubo cambios."""
    has_changes = False
    for field, new_val_raw in new_values.items():
        if new_val_raw is None and field not in ["quantity", "time", "people", "performance"]:
            continue

        curr_val = getattr(existing_code, field)

        if field in ["quantity", "time", "performance", "people"]:
            if field == "people":
                n, c = clean_int(new_val_raw), clean_int(curr_val)
            else:
                n, c = clean_float(new_val_raw), clean_float(curr_val)

            if n != c:
                setattr(existing_code, field, str(n) if field == "quantity" and n is not None else n)
                has_changes = True
        else:
            n, c = clean_str_preserve_case(new_val_raw), clean_str_preserve_case(curr_val)
            if n != c:
                setattr(existing_code, field, n)
                has_changes = True

    return has_changes


def _build_code(code_str, activity_str, code_data, useful_life, fabrication_code) -> Code:
    """Construye un objeto Code nuevo a partir de los datos crudos del Excel."""
    qty_float = clean_float(code_data.get("quantity"))
    return Code(
        code=clean_str_preserve_case(code_str),
        activity=clean_str_preserve_case(activity_str),
        description=clean_str_preserve_case(code_data.get("description")),
        unit=clean_str_preserve_case(code_data.get("unit")),
        type=clean_str_preserve_case(code_data.get("type")),
        quantity=str(qty_float) if qty_float is not None else None,
        time=clean_float(code_data.get("time")),
        people=clean_int(code_data.get("people")),
        performance=clean_float(code_data.get("performance")),
        material=clean_str_preserve_case(code_data.get("material")),
        presentation=clean_str_preserve_case(code_data.get("presentation")),
        fabricationCode=clean_str_preserve_case(fabrication_code),
        usefulLife=clean_str_preserve_case(useful_life),
    )
