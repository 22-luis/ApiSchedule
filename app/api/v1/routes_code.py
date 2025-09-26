import logging
import re
import uuid
from typing import List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.dependency import get_db
from app.models.code import Code
from app.models.order import Order
from app.models.role import UserRole
from app.models.user import User
from app.schemas.code import CodeCreate, CodeOut, CodePageOut, CodeUpdate
from app.utils.data_cleaning import clean_float, clean_str, clean_str_preserve_case
from app.utils.dependencies import require_roles

# Configurar logger
logger = logging.getLogger(__name__)

# Importar sistema de caché
try:
    from app.utils.cache import cache_response, invalidate_cache

    CACHE_AVAILABLE = True
except ImportError:
    logger.warning("Módulo de caché no encontrado. El caché estará deshabilitado.")
    CACHE_AVAILABLE = False


    # Decoradores dummy si el caché no está disponible
    def cache_response(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


    def invalidate_cache(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

router = APIRouter(prefix="/codes", tags=["codes"])


# --- Endpoints CRUD --- 

@router.post("/", response_model=CodeOut)
@invalidate_cache(pattern="codes")
def create_code(code: CodeCreate, db: Session = Depends(get_db),
                current_user: User = Depends(require_roles(UserRole.ADMIN))):
    db_code = Code(**code.dict())
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
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    query = db.query(Code)
    if search:
        search_pattern = f"%{search.lower()}%"
        query = query.filter(
            (Code.code.ilike(search_pattern)) |
            (Code.description.ilike(search_pattern))
        )
    
    total = query.count()
    codes = query.offset(skip).limit(limit).all()
    
    # La serialización a CodeOut se maneja automáticamente por FastAPI
    return {"codes": codes, "total": total}

@router.get("/{code_id}", response_model=CodeOut)
@cache_response(ttl=600, key_fields=["code_id"])
def get_code(code_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    return code

@router.patch("/{code_id}", response_model=CodeOut)
@invalidate_cache(pattern="codes")
def update_code(code_id: uuid.UUID, code_update: CodeUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    
    update_data = code_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_code, field, value)
    
    db.commit()
    db.refresh(db_code)
    return db_code

@router.delete("/{code_id}")
@invalidate_cache(pattern="codes")
def delete_code(code_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    db.delete(db_code)
    db.commit()
    return {"message": "Code deleted successfully"}

# --- Endpoints de Búsqueda y Específicos ---

@router.get("/by_code_and_activity", response_model=CodeOut)
@cache_response(ttl=600, key_fields=["code", "activity"])
def get_code_by_code_and_activity(code: str, activity: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
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
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    logger.debug(f"Buscando detalles para código '{code}' y actividad '{activity}'")
    
    code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
    if not code_obj:
        logger.warning(f"No se encontró código '{code}' con actividad '{activity}'")
        raise HTTPException(status_code=404, detail=f"No se encontró código '{code}' con actividad '{activity}'")
    
    # El response model se encargará de la serialización
    return {
        "success": True,
        "code": code,
        "activity": activity,
        "activity_details": code_obj, # Retornar el objeto directamente
        "message": f"Datos obtenidos exitosamente para código '{code}' y actividad '{activity}'"
    }

@router.get("/by_code/{code}/activity")
@cache_response(ttl=600, key_fields=["code"])
def get_code_activity(code: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code_objs = db.query(Code).filter(Code.code == code).all()
    if not code_objs:
        raise HTTPException(status_code=404, detail="Code not found")
    
    return {
        "code": code,
        "activities": code_objs, # Retornar la lista de objetos directamente
        "total_activities": len(code_objs)
    }

@router.get("/by_code/{code}/lotes")
@cache_response(ttl=300, key_fields=["code"])
def get_lotes_by_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    lotes = db.query(Order.lote).filter(
        Order.code == code,
        Order.status != "completed"
    ).all()
    
    return {
        "code": code,
        "lotes": [l[0] for l in lotes if l[0] is not None]
    }

# --- Endpoints de Carga Masiva y Debug ---

from pydantic import BaseModel
from typing import Optional, Any

class CodeBulkItem(BaseModel):
    code: str
    activity: Optional[str]
    description: Optional[str]
    unit: Optional[str]
    type: Optional[str]
    quantity: Optional[Any]
    time: Optional[Any]
    people: Optional[Any]
    performance: Optional[Any]
    material: Optional[str]
    presentation: Optional[str]
    fabricationCode: Optional[str]
    usefulLife: Optional[str]

    class Config:
        extra = "allow" # Permitir otros campos que puedan venir del Excel

@router.post("/bulk_upload")
@invalidate_cache(pattern="codes")
def bulk_upload_codes(codes: List[CodeBulkItem], db: Session = Depends(get_db), current_user=Depends(require_roles(UserRole.ADMIN))):
    logger.info(f"Iniciando carga masiva con {len(codes)} registros")
    
    all_db_codes = db.query(Code).all()
    existing_codes_map = {
        (clean_str(c.code), clean_str(c.activity)): c for c in all_db_codes
    }
    logger.info(f"Se cargaron {len(existing_codes_map)} códigos existentes en memoria para comparación.")

    created, updated, errors = 0, 0, []
    
    for idx, item in enumerate(codes):
        code_data = item.dict(exclude_unset=True) # Usar el dict del modelo pydantic
        code_str = code_data.get("code")
        
        if not code_str: # Pydantic ya valida esto, pero es una doble seguridad
            errors.append({"row": idx + 2, "error": "Fila sin código"})
            continue

        # 2. PROCESAR: Limpiar y buscar en el mapa en memoria
        activity_str = code_data.get("activity")
        lookup_key = (clean_str(code_str), clean_str(activity_str))
        existing_code = existing_codes_map.get(lookup_key)

        # Mapeo de columnas para compatibilidad con Excel (lowercase a camelCase)
        useful_life = code_data.get("usefulLife") or code_data.get("usefullife")
        fabrication_code = code_data.get("fabricationCode") or code_data.get("fabricationc")

        if existing_code:
            # 3. ACTUALIZAR (si hay cambios)
            has_changes = False
            new_values = {
                'description': clean_str_preserve_case(code_data.get("description")),
                'unit': clean_str_preserve_case(code_data.get("unit")),
                'type': clean_str_preserve_case(code_data.get("type")),
                'quantity': clean_float(code_data.get("quantity")),
                'time': clean_float(code_data.get("time")),
                'people': clean_float(code_data.get("people")),
                'performance': clean_float(code_data.get("performance")),
                'material': clean_str_preserve_case(code_data.get("material")),
                'presentation': clean_str_preserve_case(code_data.get("presentation")),
                'fabricationCode': clean_str_preserve_case(fabrication_code),
                'usefulLife': clean_str_preserve_case(useful_life)
            }

            for field, new_value in new_values.items():
                current_value = getattr(existing_code, field)
                if isinstance(current_value, str) and isinstance(new_value, str):
                    if clean_str(current_value) != clean_str(new_value):
                        setattr(existing_code, field, new_value)
                        has_changes = True
                elif current_value != new_value:
                    setattr(existing_code, field, new_value)
                    has_changes = True
            
            if has_changes:
                updated += 1
        else:
            # 4. CREAR (si no existe)
            new_code = Code(
                code=clean_str_preserve_case(code_str),
                activity=clean_str_preserve_case(activity_str),
                description=clean_str_preserve_case(code_data.get("description")),
                unit=clean_str_preserve_case(code_data.get("unit")),
                type=clean_str_preserve_case(code_data.get("type")),
                quantity=clean_float(code_data.get("quantity")),
                time=clean_float(code_data.get("time")),
                people=clean_float(code_data.get("people")),
                performance=clean_float(code_data.get("performance")),
                material=clean_str_preserve_case(code_data.get("material")),
                presentation=clean_str_preserve_case(code_data.get("presentation")),
                fabricationCode=clean_str_preserve_case(fabrication_code),
                usefulLife=clean_str_preserve_case(useful_life)
            )
            db.add(new_code)
            created += 1
            # Añadir el nuevo código al mapa para evitar duplicados en la misma carga
            existing_codes_map[lookup_key] = new_code

    # 5. COMMIT: Guardar todos los cambios en una sola transacción
    if created > 0 or updated > 0:
        db.commit()
        logger.info(f"Commit a la BD realizado. Creados: {created}, Actualizados: {updated}")
    
    total_processed = len(codes) - len(errors)
    unchanged = total_processed - created - updated
    
    logger.info(f"Carga masiva completada - Creados: {created}, Actualizados: {updated}, Sin cambios: {unchanged}, Errores: {len(errors)}")
    
    return {
        "created": created, 
        "updated": updated, 
        "unchanged": unchanged,
        "errors": errors,
        "total_processed": total_processed,
    }
