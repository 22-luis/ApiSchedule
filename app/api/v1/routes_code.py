"""
Rutas de la API para la gestión de códigos predefinidos: creación, actualización, eliminación, consulta con paginación, búsqueda y carga masiva.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.models.code import Code
from app.schemas.code import CodeCreate, CodeUpdate, CodeOut, CodePageOut
from app.db.dependency import get_db
from app.models.user import User
from app.utils.dependencies import require_roles
from app.models.role import UserRole
import uuid
from app.models.task import Task
from app.models.order import Order

# Importar sistema de caché
try:
    from app.utils.cache import cache_response, invalidate_cache
    CACHE_AVAILABLE = True
except ImportError:
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



def clean_float(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
        if value == '' or value == '-' or value.lower() == 'null':
            return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def clean_str(value):
    if value is None:
        return ""
    if isinstance(value, str):
        # Limpiar espacios múltiples, caracteres especiales y normalizar
        cleaned = value.strip().replace('\xa0', ' ')
        # Reemplazar múltiples espacios con uno solo
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.upper() if cleaned.lower() != 'null' else ""
    return str(value).strip().upper()

@router.post("/", response_model=CodeOut)
@invalidate_cache(pattern="codes")  # Invalidar caché de códigos
def create_code(code: CodeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_code = Code(
        code=code.code,
        description=code.description,
        unit=code.unit,
        type=code.type,
        activity=code.activity,
        quantity=code.quantity,
        time=code.time,
        people=code.people,
        performance=code.performance,
        material=code.material,
        presentation=code.presentation,
        fabricationCode=code.fabricationCode,
        usefulLife=code.usefulLife
    )
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return {
        "id": db_code.id,
        "code": db_code.code,
        "description": db_code.description,
        "unit": db_code.unit,
        "type": db_code.type,
        "activity": db_code.activity,
        "quantity": db_code.quantity,
        "time": db_code.time,
        "people": db_code.people,
        "performance": db_code.performance,
        "material": db_code.material,
        "presentation": db_code.presentation,
        "fabricationCode": db_code.fabricationCode,
        "usefulLife": db_code.usefulLife,
    }

@router.get("/debug_codes")
def debug_codes(db: Session = Depends(get_db)):
    """Endpoint temporal para debug - ver todos los códigos"""
    try:
        codes = db.query(Code).all()
        result = []
        for code in codes:
            result.append({
                "id": str(code.id),
                "code": f"'{code.code}'",
                "activity": f"'{code.activity}'",
                "description": f"'{code.description}'",
                "code_len": len(code.code or ""),
                "activity_len": len(code.activity or ""),
                "code_repr": repr(code.code),
                "activity_repr": repr(code.activity)
            })
        return {"total": len(codes), "codes": result[:10]}  # Solo primeros 10 para no saturar
    except Exception as e:
        return {"error": str(e), "total": 0, "codes": []}

@router.post("/test_search")
def test_search(search_data: dict, db: Session = Depends(get_db)):
    """Endpoint para probar la búsqueda de códigos"""
    try:
        code_str = search_data.get("code", "")
        activity_str = search_data.get("activity", "")
        
        print(f"[TEST_SEARCH] Buscando código='{code_str}' actividad='{activity_str}'")
        
        # Limpiar valores
        clean_code = clean_str(code_str)
        clean_activity = clean_str(activity_str)
        
        print(f"[TEST_SEARCH] Limpiados código='{clean_code}' actividad='{clean_activity}'")
        
        # Buscar
        existing_code = db.query(Code).filter(
            Code.code == clean_code,
            Code.activity == clean_activity
        ).first()
        
        if existing_code:
            result = {
                "found": True,
                "id": str(existing_code.id),
                "code": existing_code.code,
                "activity": existing_code.activity,
                "description": existing_code.description
            }
        else:
            result = {"found": False}
        
        print(f"[TEST_SEARCH] Resultado: {result}")
        return result
        
    except Exception as e:
        return {"error": str(e), "found": False}

@router.post("/bulk_upload")
@invalidate_cache(pattern="codes")  # Invalidar caché de códigos
def bulk_upload_codes(codes: list[dict], db: Session = Depends(get_db), current_user=Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    print(f"[BULK_UPLOAD] Iniciando carga masiva con {len(codes)} registros")
    
    # Lista de actividades permitidas
    ACTIVIDADES_PERMITIDAS = {
        "EMPAQUE MANUAL MAS MEZCLA",
        "EMPAQUE MANUAL GRUPO", 
        "EMPAQUE MANUAL",
        "EMPAQUE MAQUINA SEMI AUTOMATICA",
        "EMPAQUE MAQUINA AUTOMATICA",
        "PESADO",
        "MOLIENDA EN POLVO",
        "MOLIENDA EN PASTA",
        "MEZCLA MANUAL POLVO",
        "MEZCLA EN MAQUINA",
        "MEZCLA LIQUIDA",
        "FABRICACION DE ADEREZOS, JALEAS",
        "HOMOGENIZACION"
    }
    
    created = 0
    updated = 0
    errors = []
    ignored = 0
    
    for idx, code_data in enumerate(codes):
        code_str = code_data.get("code")
        description = code_data.get("description")
        activity = code_data.get("activity")
        
        if not code_str:
            errors.append({"row": idx+1, "error": "Falta código"})
            continue
        
        # Mapeo de columnas para compatibilidad con Excel (lowercase a camelCase)
        useful_life = code_data.get("usefulLife") or code_data.get("usefullife")
        fabrication_code = code_data.get("fabricationCode") or code_data.get("fabricationc")
        
        # Limpiar el código y la actividad antes de buscar
        clean_code = clean_str(code_str)
        clean_activity = clean_str(activity)
        
        print(f"[DEBUG] Fila {idx+1}: Buscando código='{clean_code}' (len={len(clean_code)}) actividad='{clean_activity}' (len={len(clean_activity)})")
        
        # Validar que la actividad esté en la lista permitida
        # if clean_activity not in ACTIVIDADES_PERMITIDAS:
        #     print(f"[DEBUG] Actividad '{clean_activity}' no está permitida. Ignorando registro.")
        #     errors.append({"row": idx+1, "error": f"Actividad no permitida: '{activity}'. Actividades válidas: {', '.join(sorted(ACTIVIDADES_PERMITIDAS))}"})
        #     ignored += 1
        #     continue
        
        # Buscar todos los códigos que coincidan y comparar manualmente con normalización
        all_codes = db.query(Code).filter(Code.code.ilike(clean_code)).all()
        existing_code = None
        
        print(f"[DEBUG] Encontrados {len(all_codes)} códigos con código similar")
        
        for code_obj in all_codes:
            db_code_clean = clean_str(code_obj.code)
            db_activity_clean = clean_str(code_obj.activity)
            
            print(f"[DEBUG] Comparando: DB('{db_code_clean}','{db_activity_clean}') vs Excel('{clean_code}','{clean_activity}')")
            
            if db_code_clean == clean_code and db_activity_clean == clean_activity:
                existing_code = code_obj
                print(f"[DEBUG] ¡COINCIDENCIA ENCONTRADA! ID: {existing_code.id}")
                break
        
        if not existing_code:
            print(f"[DEBUG] NO ENCONTRADO - Creando nuevo registro")
        
        if existing_code:
            # Si existe, actualizar solo los campos que han cambiado
            has_changes = False
            
            # Preparar los nuevos valores preservando formato original
            def clean_str_preserve_case(value):
                if value is None:
                    return ""
                if isinstance(value, str):
                    cleaned = value.strip().replace('\xa0', ' ')
                    import re
                    cleaned = re.sub(r'\s+', ' ', cleaned)
                    return cleaned if cleaned.lower() != 'null' else ""
                return str(value).strip()
            
            new_values = {
                'description': clean_str_preserve_case(description),
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
            
            # Comparar y actualizar solo los campos diferentes
            for field, new_value in new_values.items():
                current_value = getattr(existing_code, field)
                # Normalizar valores para comparación (pero mantener formato original al guardar)
                if isinstance(current_value, str) and isinstance(new_value, str):
                    # Normalizar ambos para comparación
                    current_normalized = clean_str(current_value) if current_value else ""
                    new_normalized = clean_str(new_value) if new_value else ""
                    if current_normalized != new_normalized:
                        setattr(existing_code, field, new_value)  # Guardar el valor original
                        has_changes = True
                        print(f"[DEBUG] Campo '{field}' cambiado: '{current_value}' -> '{new_value}'")
                elif current_value != new_value:
                    setattr(existing_code, field, new_value)
                    has_changes = True
                    print(f"[DEBUG] Campo '{field}' cambiado: {current_value} -> {new_value}")
            
            if has_changes:
                updated += 1
        else:
            # Si no existe, crear nuevo
            # Para crear, usar valores limpios pero manteniendo el formato original
            def clean_str_preserve_case(value):
                if value is None:
                    return ""
                if isinstance(value, str):
                    cleaned = value.strip().replace('\xa0', ' ')
                    import re
                    cleaned = re.sub(r'\s+', ' ', cleaned)
                    return cleaned if cleaned.lower() != 'null' else ""
                return str(value).strip()
            
            db_code = Code(
                code=clean_str_preserve_case(code_str),
                description=clean_str_preserve_case(description),
                unit=clean_str_preserve_case(code_data.get("unit")),
                type=clean_str_preserve_case(code_data.get("type")),
                activity=clean_str_preserve_case(activity),
                quantity=clean_float(code_data.get("quantity")),
                time=clean_float(code_data.get("time")),
                people=clean_float(code_data.get("people")),
                performance=clean_float(code_data.get("performance")),
                material=clean_str_preserve_case(code_data.get("material")),
                presentation=clean_str_preserve_case(code_data.get("presentation")),
                fabricationCode=clean_str_preserve_case(fabrication_code),
                usefulLife=clean_str_preserve_case(useful_life)
            )
            db.add(db_code)
            created += 1
    
    db.commit()
    
    # Calcular registros sin cambios
    total_processed = len(codes) - len(errors)
    unchanged = total_processed - created - updated
    
    print(f"[BULK_UPLOAD] Completado - Creados: {created}, Actualizados: {updated}, Sin cambios: {unchanged}, Ignorados: {ignored}, Errores: {len(errors)}")
    
    return {
        "created": created, 
        "updated": updated, 
        "unchanged": unchanged,
        "ignored": ignored,
        "errors": errors,
        "total_processed": total_processed,
        "valid_activities": list(ACTIVIDADES_PERMITIDAS)
    }

@router.get("/", response_model=CodePageOut)
@cache_response(ttl=300, key_fields=["skip", "limit", "search"])  # Cache por 5 minutos
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
    result = []
    for c in codes:
        result.append({
            "id": c.id,
            "code": clean_str(c.code),
            "description": clean_str(c.description),
            "unit": clean_str(c.unit),
            "type": clean_str(c.type),
            "activity": clean_str(c.activity),
            "quantity": c.quantity,
            "time": c.time,
            "people": c.people,
            "performance": c.performance,
            "material": clean_str(c.material),
            "presentation": clean_str(c.presentation),
            "fabricationCode": clean_str(c.fabricationCode),
            "usefulLife": clean_str(c.usefulLife),
        })
    return {"codes": result, "total": total}

@router.get("/by_code_and_activity")
@cache_response(ttl=600, key_fields=["code", "activity"])  # Cache por 10 minutos
def get_code_by_code_and_activity(code: str, activity: str, db: Session = Depends(get_db)):
    code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
    if not code_obj:
        raise HTTPException(status_code=404, detail="Code not found with given code and activity")
    return code_obj

@router.get("/by_code_and_activity_details")
@cache_response(ttl=600, key_fields=["code", "activity"])  # Cache por 10 minutos
def get_activity_details_by_code_and_activity(
    code: str, 
    activity: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Obtiene los datos detallados de una actividad específica basándose en el código y la actividad.
    
    Args:
        code: Código del producto
        activity: Nombre de la actividad
        
    Returns:
        Datos detallados de la actividad incluyendo specification, people, performance, material, etc.
    """
    print(f"[DEBUG] get_activity_details_by_code_and_activity: Buscando código '{code}' y actividad '{activity}'")
    
    code_obj = db.query(Code).filter(Code.code == code, Code.activity == activity).first()
    
    if not code_obj:
        print(f"[DEBUG] get_activity_details_by_code_and_activity: No se encontró código '{code}' con actividad '{activity}'")
        raise HTTPException(status_code=404, detail=f"No se encontró código '{code}' con actividad '{activity}'")
    
    # Obtener todos los campos solicitados
    activity_details = {
        "id": str(code_obj.id),
        "code": code_obj.code,
        "activity": code_obj.activity,
        "specification": getattr(code_obj, "specification", None),  # Campo que puede no existir
        "people": code_obj.people,
        "performance": code_obj.performance,
        "material": code_obj.material,
        "presentation": code_obj.presentation,
        "fabricationCode": code_obj.fabricationCode,
        "usefulLife": code_obj.usefulLife,
        "unit": code_obj.unit,
        "type": code_obj.type,
        "description": code_obj.description,
        "quantity": code_obj.quantity,
        "time": code_obj.time
    }
    
    print(f"[DEBUG] get_activity_details_by_code_and_activity: Encontrados datos para código '{code}' y actividad '{activity}'")
    print(f"[DEBUG] get_activity_details_by_code_and_activity: Datos - {activity_details}")
    
    return {
        "success": True,
        "code": code,
        "activity": activity,
        "activity_details": activity_details,
        "message": f"Datos obtenidos exitosamente para código '{code}' y actividad '{activity}'"
    }

@router.get("/by_code/{code}/activity")
@cache_response(ttl=600, key_fields=["code"])  # Cache por 10 minutos
def get_code_activity(code: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code_objs = db.query(Code).filter(Code.code == code).all()
    if not code_objs:
        raise HTTPException(status_code=404, detail="Code not found")
    
    activities = []
    for code_obj in code_objs:
        activities.append({
            "id": code_obj.id,
            "activity": getattr(code_obj, "activity", None),
            "description": getattr(code_obj, "description", None),
            "unit": getattr(code_obj, "unit", None),
            "type": getattr(code_obj, "type", None),
            "quantity": getattr(code_obj, "quantity", None),
            "time": getattr(code_obj, "time", None),
            "people": getattr(code_obj, "people", None),
            "performance": getattr(code_obj, "performance", None),
            "material": getattr(code_obj, "material", None),
            "presentation": getattr(code_obj, "presentation", None),
            "fabricationCode": getattr(code_obj, "fabricationCode", None),
            "usefulLife": getattr(code_obj, "usefulLife", None)
        })
    
    return {
        "code": code,
        "activities": activities,
        "total_activities": len(activities)
    }

@router.get("/by_code/{code}/lotes")
@cache_response(ttl=300, key_fields=["code"])  # Cache por 5 minutos
def get_lotes_by_code(code: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    # Obtener todos los lotes excepto los que tienen estado "completed" (completado)
    lotes = db.query(Order.lote).filter(
        Order.code == code,
        Order.status != "completed"
    ).all()
    
    # Devolver respuesta vacía en lugar de error 404 cuando no hay lotes
    return {
        "code": code,
        "lotes": [l[0] for l in lotes if l[0] is not None]
    }

@router.get("/{code_id}", response_model=CodeOut)
@cache_response(ttl=600, key_fields=["code_id"])  # Cache por 10 minutos
def get_code(code_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))):
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    return {
        "id": code.id,
        "code": code.code,
        "description": code.description,
        "unit": code.unit,
        "type": code.type,
        "activity": code.activity,
        "quantity": code.quantity,
        "time": code.time,
        "people": code.people,
        "performance": code.performance,
        "material": code.material,
        "presentation": code.presentation,
        "fabricationCode": code.fabricationCode,
        "usefulLife": code.usefulLife,
    }

@router.patch("/{code_id}", response_model=CodeOut)
@invalidate_cache(pattern="codes")  # Invalidar caché de códigos
def update_code(code_id: uuid.UUID, code_update: CodeUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    update_data = code_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_code, field, value)
    db.commit()
    db.refresh(db_code)
    return {
        "id": db_code.id,
        "code": db_code.code,
        "description": db_code.description,
        "unit": db_code.unit,
        "type": db_code.type,
        "activity": db_code.activity,
        "quantity": db_code.quantity,
        "time": db_code.time,
        "people": db_code.people,
        "performance": db_code.performance,
        "material": db_code.material,
        "presentation": db_code.presentation,
        "fabricationCode": db_code.fabricationCode,
        "usefulLife": db_code.usefulLife,
    }

@router.delete("/{code_id}")
@invalidate_cache(pattern="codes")  # Invalidar caché de códigos
def delete_code(code_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_code = db.query(Code).filter(Code.id == code_id).first()
    if not db_code:
        raise HTTPException(status_code=404, detail="Code not found")
    db.delete(db_code)
    db.commit()
    return {"message": "Code deleted successfully"} 