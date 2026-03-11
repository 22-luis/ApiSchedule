import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, cast, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session

from app.modules.quality.models.catalog_test import CatalogTest
from app.modules.codes.models.code import Code
from app.modules.quality.models.code_test import CodeTest
from app.modules.codes.schemas.code import CodeCreate, CodeOut, CodePageOut, CodeUpdate
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.orders.models.order import Order
from app.shared.core.enums import (
    WeighingActivities,
    ManufacturingActivities
)
from app.shared.db.session import get_db
from app.shared.utils.business.data_cleaning import clean_float, clean_int, clean_str, clean_str_preserve_case
from app.shared.utils.core.dependencies import require_roles

# Configurar logger
logger = logging.getLogger(__name__)

# Importar sistema de caché
try:
    from app.shared.utils.cache import cache_response, invalidate_cache

    CACHE_AVAILABLE = True
except ImportError:
    logger.info("Módulo de caché no encontrado. El caché estará deshabilitado.")
    CACHE_AVAILABLE = False


    # Decoradores dummy si el caché no está disponible
    def cache_response(*_args, **_kwargs):
        def decorator(fn):
            return fn

        return decorator


    def invalidate_cache(*_args, **_kwargs):
        def decorator(fn):
            return fn

        return decorator

router = APIRouter(prefix="/codes", tags=["codes"])


# --- Endpoints CRUD --- 

@router.post("/", response_model=CodeOut)
@invalidate_cache(pattern="codes")
def create_code(code: CodeCreate, db: Session = Depends(get_db),
                _current_user: User = Depends(require_roles(UserRole.ADMIN))):
    db_code = Code(**code.model_dump())
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return db_code

@router.get("/", response_model=CodePageOut)
@cache_response(ttl=300, key_fields=["skip", "limit", "search"])
def get_codes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de registros a devolver"),
    search: str = Query(None, description="Buscar por código o descripción"),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    query = db.query(Code)
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.filter(
            (Code.code.ilike(search_pattern)) |
            (Code.description.ilike(search_pattern))
        )
    
    total = query.count()
    codes = query.order_by(Code.code).offset(skip).limit(limit).all()
    
    return CodePageOut(
        codes=[CodeOut.model_validate(c) for c in codes],
        total=total
    )

@router.get("/production", response_model=CodePageOut)
@cache_response(ttl=300, key_fields=["skip", "limit", "search"])
def get_production_codes(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de registros a devolver"),
    search: str = Query(None, description="Buscar por código o descripción"),
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.QC_COORDINATOR, UserRole.QC_ASSISTANT))
):
    production_activities = [
        WeighingActivities.PESADO,
        ManufacturingActivities.FABRICACION,
        ManufacturingActivities.MOL_PASTA,
        ManufacturingActivities.MOL_POLVO,
        ManufacturingActivities.MEZ_MAQUINA,
        ManufacturingActivities.MEZ_POLVO,
        ManufacturingActivities.MEZ_LIQUIDA
    ]

    subquery = db.query(
        func.min(cast(Code.id, String)).cast(UUID).label("min_id")
    ).filter(
        Code.activity.in_(production_activities)
    )

    if search:
        search_pattern = f"%{search.lower()}%"
        subquery = subquery.filter(
            (Code.code.ilike(search_pattern)) |
            (Code.description.ilike(search_pattern))
        )
    
    subquery = subquery.group_by(Code.code).subquery()

    query = db.query(Code).filter(Code.id.in_(db.query(subquery.c.min_id)))
    
    total = query.count()
    codes = query.order_by(Code.code).offset(skip).limit(limit).all()
    # Cargar pruebas vinculadas a los códigos obtenidos
    code_ids = [c.id for c in codes]
    if code_ids:
        rows = db.query(CodeTest.code_id, CatalogTest).join(CatalogTest, CatalogTest.id == CodeTest.catalog_test_id).filter(CodeTest.code_id.in_(code_ids)).all()
        tests_map = {}
        for code_id, test in rows:
            tests_map.setdefault(code_id, []).append(test)
        for c in codes:
            setattr(c, "tests", tests_map.get(c.id, []))
    
    return CodePageOut(
        codes=[CodeOut.model_validate(c) for c in codes],
        total=total
    )

@router.get("/{code_id}", response_model=CodeOut)
@cache_response(ttl=600, key_fields=["code_id"])
def get_code(code_id: uuid.UUID, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    return code

@router.patch("/{code_id}", response_model=CodeOut)
@invalidate_cache(pattern="codes")
def update_code(code_id: uuid.UUID, code_update: CodeUpdate, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    
    update_data = code_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_code, field, value)
    
    db.commit()
    db.refresh(db_code)
    return db_code

@router.delete("/{code_id}")
@invalidate_cache(pattern="codes")
def delete_code(code_id: uuid.UUID, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    db.delete(db_code)
    db.commit()
    return {"message": "Code deleted successfully"}

# --- Endpoints de Búsqueda y Específicos ---

@router.get("/by_code_and_activity", response_model=CodeOut)
@cache_response(ttl=600, key_fields=["code", "activity"])
def get_code_by_code_and_activity(code: str, activity: str, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
    if not code_obj:
        raise HTTPException(status_code=404, detail="Code not found with given code and activity")
    return code_obj

@router.get("/by_code_and_activity_details")
@cache_response(ttl=600, key_fields=["code", "activity"])
def get_activity_details_by_code_and_activity(
    code: str, 
    activity: str, 
    db: Session = Depends(get_db), 
    _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    logger.debug(f"Buscando detalles para código '{code}' y actividad '{activity}'")
    
    code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
    if not code_obj:
        logger.warning(f"No se encontró código '{code}' con actividad '{activity}'")
        raise HTTPException(status_code=404, detail=f"No se encontró código '{code}' con actividad '{activity}'")
    
    return {
        "success": True,
        "code": code,
        "activity": activity,
        "activity_details": code_obj, 
        "message": f"Datos obtenidos exitosamente para código '{code}' y actividad '{activity}'"
    }

@router.get("/by_code/{code}/activity")
@cache_response(ttl=600, key_fields=["code"])
def get_code_activity(code: str, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code_objs = db.query(Code).filter(Code.code == code).all()
    if not code_objs:
        raise HTTPException(status_code=404, detail="Code not found")
    
    return {
        "code": code,
        "activities": code_objs,
        "total_activities": len(code_objs)
    }

@router.get("/by_code/{code}/lotes")
@cache_response(ttl=300, key_fields=["code"])
def get_lotes_by_code(code: str, db: Session = Depends(get_db), _current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    lotes = db.query(Order.lote).filter(
        Order.code == code,
        Order.status != "completed"
    ).all()
    
    return {
        "code": code,
        "lotes": [l[0] for l in lotes if l[0] is not None]
    }

# --- Endpoints de Carga Masiva y Debug ---

from pydantic import BaseModel, ValidationError, ConfigDict
from typing import Optional, Any

class CodeBulkItem(BaseModel):
    id: Optional[uuid.UUID] = None
    code: str
    activity: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    type: Optional[str] = None
    quantity: Optional[Any] = None
    time: Optional[Any] = None
    people: Optional[Any] = None
    performance: Optional[Any] = None
    material: Optional[str] = None
    presentation: Optional[str] = None
    fabricationCode: Optional[str] = None
    usefulLife: Optional[str] = None
    verification: Optional[Any] = None

    model_config = ConfigDict(extra='allow') # Permitir otros campos que puedan venir del Excel

@router.post("/bulk_upload")
@invalidate_cache(pattern="codes")
def bulk_upload_codes(codes: List[dict], db: Session = Depends(get_db), _current_user=Depends(require_roles(UserRole.ADMIN))):
    logger.info(f"Iniciando carga masiva con {len(codes)} registros")
    
    all_db_codes = db.query(Code).all()
    existing_codes_map = {
        (clean_str(c.code), clean_str(c.activity)): c for c in all_db_codes
    }
    existing_ids_map = {c.id: c for c in all_db_codes}
    logger.info(f"Se cargaron {len(existing_codes_map)} códigos existentes en memoria para comparación.")

    created, updated, deleted, errors = 0, 0, 0, []
    processed_ids = set()
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

        # 2. PROCESAR: Limpiar y buscar en el mapa en memoria
        activity_str = code_data.get("activity")
        lookup_key = (clean_str(code_str), clean_str(activity_str))
        
        # Intentar buscar por ID si viene en el Excel, sino por código y actividad
        existing_code = None
        if item_id and item_id in existing_ids_map:
            existing_code = existing_ids_map[item_id]
        else:
            existing_code = existing_codes_map.get(lookup_key)

        # Mapeo de columnas para compatibilidad con Excel (lowercase a camelCase)
        useful_life = code_data.get("usefulLife") or code_data.get("usefullife")
        fabrication_code = code_data.get("fabricationCode") or code_data.get("fabricationc")

        if existing_code:
            # 3. ACTUALIZAR (si hay cambios)
            new_values_to_compare = {
                'description': code_data.get("description"),
                'unit': code_data.get("unit"),
                'type': code_data.get("type"),
                'quantity': code_data.get("quantity"),
                'time': code_data.get("time"),
                'people': code_data.get("people"),
                'performance': code_data.get("performance"),
                'material': code_data.get("material"),
                'presentation': code_data.get("presentation"),
                'fabricationCode': fabrication_code,
                'usefulLife': useful_life,
                'verification': code_data.get("verification")
            }
            # También actualizar código y actividad si se encontró por ID
            if item_id:
                new_values_to_compare['code'] = code_data.get("code")
                new_values_to_compare['activity'] = code_data.get("activity")

            has_changes = False
            for field, new_val_raw in new_values_to_compare.items():
                if new_val_raw is None and field not in ['quantity', 'time', 'people', 'performance']:
                    continue
                
                curr_val = getattr(existing_code, field)
                
                # Comparación robusta por tipo
                if field in ['quantity', 'time', 'performance', 'people', 'verification']:
                    # Campos numéricos o booleanos
                    if field == 'people':
                        n = clean_int(new_val_raw)
                        c = clean_int(curr_val)
                    elif field == 'verification':
                        # Convertir a booleano de forma robusta
                        if isinstance(new_val_raw, str):
                            n = new_val_raw.lower() in ('true', '1', 't', 'y', 'yes', 'si', 'sí')
                        else:
                            n = bool(new_val_raw) if new_val_raw is not None else False
                        c = bool(curr_val)
                    else:
                        n = clean_float(new_val_raw)
                        c = clean_float(curr_val)
                    
                    if n != c:
                        # Si es quantity, guardamos como string si no es None
                        if field == 'quantity':
                            setattr(existing_code, field, str(n) if n is not None else None)
                        else:
                            setattr(existing_code, field, n)
                        has_changes = True
                else:
                    # Campos string: normalizamos para evitar actualizaciones por espacios o None vs ""
                    n = clean_str_preserve_case(new_val_raw)
                    c = clean_str_preserve_case(curr_val)
                    if n != c:
                        setattr(existing_code, field, n)
                        has_changes = True
            
            if has_changes:
                updated += 1
                logger.debug(f"Código {existing_code.code} (ID: {existing_code.id}) actualizado por cambios.")
            processed_ids.add(existing_code.id)
        else:
            # 4. CREAR (si no existe)
            new_code = Code(
                code=clean_str_preserve_case(code_str),
                activity=clean_str_preserve_case(activity_str),
                description=clean_str_preserve_case(code_data.get("description")),
                unit=clean_str_preserve_case(code_data.get("unit")),
                type=clean_str_preserve_case(code_data.get("type")),
                quantity=str(clean_float(code_data.get("quantity"))) if clean_float(code_data.get("quantity")) is not None else None,
                time=clean_float(code_data.get("time")),
                people=clean_int(code_data.get("people")),
                performance=clean_float(code_data.get("performance")),
                material=clean_str_preserve_case(code_data.get("material")),
                presentation=clean_str_preserve_case(code_data.get("presentation")),
                fabricationCode=clean_str_preserve_case(fabrication_code),
                usefulLife=clean_str_preserve_case(useful_life),
                verification=code_data.get("verification") if isinstance(code_data.get("verification"), bool) else (str(code_data.get("verification")).lower() in ('true', '1', 't', 'y', 'yes', 'si', 'sí') if code_data.get("verification") is not None else False)
            )
            db.add(new_code)
            db.flush() # Para obtener el ID generado
            created += 1
            processed_ids.add(new_code.id)
            # Añadir el nuevo código al mapa para evitar duplicados en la misma carga
            existing_codes_map[lookup_key] = new_code
            existing_ids_map[new_code.id] = new_code
            logger.debug(f"Nuevo código creado: {new_code.code} (ID: {new_code.id})")

    # 5. SINCRONIZACIÓN: Eliminar códigos que no están en el Excel si estamos en modo sync
    if sync_mode:
        codes_to_delete = [c for c in all_db_codes if c.id not in processed_ids]
        for c in codes_to_delete:
            logger.info(f"Sincronización: Eliminando código {c.code} (ID: {c.id}) por no estar en el Excel")
            db.delete(c)
            deleted += 1
        if deleted > 0:
            logger.info(f"Sincronización completa. Eliminados: {deleted}")

    # 6. COMMIT: Guardar todos los cambios en una sola transacción
    if created > 0 or updated > 0 or deleted > 0:
        db.commit()
        logger.info(f"Commit a la BD realizado. Creados: {created}, Actualizados: {updated}, Eliminados: {deleted}")
    
    total_processed = len(codes) - len(errors)
    unchanged = total_processed - created - updated
    
    logger.info(f"Carga masiva completada - Creados: {created}, Actualizados: {updated}, Eliminados: {deleted}, Sin cambios: {unchanged}, Errores: {len(errors)}")
    
    return {
        "created": created, 
        "updated": updated, 
        "deleted": deleted,
        "unchanged": unchanged,
        "errors": errors,
        "total_processed": total_processed,
    }
