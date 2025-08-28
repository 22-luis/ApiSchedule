"""
Rutas de la API para la gestión de órdenes de producción: creación, actualización de estado, eliminación y consulta con filtros.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate, OrderPageOut
from app.models import order as order_model
from app.db.dependency import get_db
from typing import List, Union, Optional
from app.models.user import User
from app.utils.dependencies import get_current_user, require_roles
from app.models.role import UserRole
from app.models.state import OrderStatus
from app.utils.data_cleaning import clean_order_data
from app.core.task_config import (
    extract_created_orders_data, 
    get_orders_summary
)
from app.services.factory import TaskServiceFactory

router = APIRouter(prefix="/orders", tags=["orders"])

def get_task_services():
    """Obtiene instancias de los servicios de tareas usando el factory"""
    weighing_service = TaskServiceFactory.create_weighing_service()
    fabrication_service = TaskServiceFactory.create_fabrication_service()
    return weighing_service, fabrication_service

@router.post("/")
def create_orders(
    orders: Union[OrderCreate, List[OrderCreate]],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    # Si es una sola orden, la convertimos en lista
    if isinstance(orders, OrderCreate):
        orders = [orders]
    created_orders = []
    for order in orders:
        # Verificar si la orden ya existe por el lote
        existing_order = db.query(order_model.Order).filter(order_model.Order.lote == order.lote).first()
        if existing_order:
            continue  # Omitir si ya existe
        
        # Limpiar los datos de la orden
        order_dict = order.dict()
        cleaned_order = clean_order_data(order_dict)
        
        db_order = order_model.Order(
            lote=order.lote,
            dueDate=order.dueDate,
            code=cleaned_order['code'],
            description=cleaned_order['description'],
            quantity=order.quantity,
            bin=order.bin,
            status=order.status,
        )
        db.add(db_order)
        created_orders.append(db_order)
    db.commit()
    for db_order in created_orders:
        db.refresh(db_order)
    
    print(f"[DEBUG] create_orders: Procesando {len(created_orders)} órdenes creadas")
    
    # Extraer solo lote, quantity y code de las órdenes creadas
    extracted_orders = extract_created_orders_data(created_orders)
    
    # Generar resumen simplificado
    summary = get_orders_summary(created_orders)
    
    # Obtener actividades para los códigos de las órdenes extraídas
    print(f"[DEBUG] create_orders: Obteniendo actividades para los códigos extraídos")
    
    # Obtener instancias de servicios usando el factory
    weighing_service, fabrication_service = get_task_services()
    
    # Crear instancia del servicio de empaque
    from app.services.factory import TaskServiceFactory
    packaging_service = TaskServiceFactory.create_packaging_service()
    
    activities_data = weighing_service.get_activities_for_orders(extracted_orders, db)
    
    # Crear tareas de pesado para todas las órdenes usando el servicio
    weighing_tasks_result = weighing_service.create_weighing_tasks_for_orders(extracted_orders, db)
    
    # Crear tareas de fabricación para todas las órdenes usando el servicio
    fabrication_tasks_result = fabrication_service.create_fabrication_tasks_for_orders(extracted_orders, db)
    
    # Crear tareas de empaque para todas las órdenes usando el servicio
    packaging_tasks_result = packaging_service.create_packaging_tasks_for_orders(extracted_orders, db)
    
    response_data = {
        "created_orders": extracted_orders,
        "summary": summary,
        "activities_data": activities_data,
        "weighing_tasks_result": weighing_tasks_result,
        "fabrication_tasks_result": fabrication_tasks_result,
        "packaging_tasks_result": packaging_tasks_result,
        "message": f"Se crearon {len(created_orders)} órdenes exitosamente. {weighing_tasks_result.get('tasks_created', 0)} tareas de pesado, {fabrication_tasks_result.get('tasks_created', 0)} tareas de fabricación y {packaging_tasks_result.get('tasks_created', 0)} tareas de empaque creadas."
    }
    
    print(f"[DEBUG] create_orders: Respuesta final - {response_data}")
    return response_data

@router.delete("/{order_id}")
def delete_order(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(db_order)
    db.commit()
    return {"message": "Order deleted successfully"}

@router.patch("/{order_id}/status")
def update_order_status(order_id: str, status_update: OrderStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    db_order.status = status_update.status
    db.commit()
    db.refresh(db_order)
    
    # Serializar la orden actualizada usando el esquema OrderOut
    order_dict = {
        "lote": db_order.lote,
        "code": db_order.code,
        "status": db_order.status,
        "description": db_order.description,
        "quantity": db_order.quantity,
        "bin": db_order.bin,
        "dueDate": db_order.dueDate
    }
    return order_dict

@router.post("/{order_id}/sync_status")
def sync_order_status(
    order_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Sincroniza el estado de una orden basándose en el estado actual de todas sus tareas.
    """
    from app.utils.order_status_service import OrderStatusService
    
    try:
        lote_int = int(order_id)
        OrderStatusService.sync_order_status_for_lote(db, str(lote_int))
        
        # Obtener la orden actualizada
        order = db.query(order_model.Order).filter(order_model.Order.lote == lote_int).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Crear respuesta sin usar el esquema para debug
        response_data = {
            "lote": order.lote,
            "code": order.code,
            "status": order.status,
            "description": order.description,
            "quantity": order.quantity,
            "bin": order.bin,
            "dueDate": order.dueDate
        }
        
        print(f"DEBUG - Response data: {response_data}")
        return response_data
        
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    except Exception as e:
        print(f"DEBUG - Error in sync_order_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error syncing order: {str(e)}")

@router.post("/{order_id}/sync_status_simple")
def sync_order_status_simple(
    order_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Sincroniza el estado de una orden sin validación de esquema (para debug).
    """
    from app.utils.order_status_service import OrderStatusService
    
    try:
        lote_int = int(order_id)
        
        # Obtener la orden antes de sincronizar
        order_before = db.query(order_model.Order).filter(order_model.Order.lote == lote_int).first()
        if not order_before:
            raise HTTPException(status_code=404, detail="Order not found")
        
        status_before = order_before.status
        
        # Sincronizar el estado
        OrderStatusService.sync_order_status_for_lote(db, str(lote_int))
        
        # Obtener la orden después de sincronizar
        order_after = db.query(order_model.Order).filter(order_model.Order.lote == lote_int).first()
        status_after = order_after.status
        
        return {
            "success": True,
            "order_id": order_id,
            "status_before": status_before,
            "status_after": status_after,
            "changed": status_before != status_after,
            "order": {
                "lote": order_after.lote,
                "code": order_after.code,
                "status": order_after.status,
                "description": order_after.description,
                "quantity": order_after.quantity,
                "bin": order_after.bin,
                "dueDate": order_after.dueDate
            }
        }
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    except Exception as e:
        print(f"DEBUG - Error in sync_order_status_simple: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error syncing order: {str(e)}")

@router.post("/sync_all_status")
def sync_all_orders_status(
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Sincroniza el estado de todas las órdenes basándose en el estado actual de sus tareas.
    """
    from app.utils.order_status_service import OrderStatusService
    
    # Obtener todas las órdenes
    orders = db.query(order_model.Order).all()
    synced_count = 0
    
    for order in orders:
        try:
            OrderStatusService.sync_order_status_for_lote(db, str(order.lote))
            synced_count += 1
        except Exception as e:
            print(f"Error syncing order {order.lote}: {e}")
            continue
    
    return {
        "message": f"Synced {synced_count} out of {len(orders)} orders",
        "synced_count": synced_count,
        "total_orders": len(orders)
    }

@router.post("/update_status_for_today")
def update_orders_status_for_today(
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Actualiza automáticamente el estado de las órdenes que tienen tareas programadas para hoy.
    Cambia de 'pending' o 'programada' a 'in_progress' si la programación es para hoy.
    """
    from app.utils.order_status_service import OrderStatusService
    from app.models.programming import ProgrammingTask
    from datetime import date
    
    today = date.today()
    updated_count = 0
    
    # Obtener todas las programaciones de tareas para hoy
    today_programming_tasks = db.query(ProgrammingTask).join(
        ProgrammingTask.programming
    ).filter(
        ProgrammingTask.programming.has(date=today)
    ).all()
    
    for pt in today_programming_tasks:
        try:
            OrderStatusService.update_order_status_for_programming_date(db, pt)
            updated_count += 1
        except Exception as e:
            print(f"Error updating order status for programming task: {e}")
            continue
    
    return {
        "message": f"Updated {updated_count} orders for today's programming",
        "updated_count": updated_count,
        "total_today_tasks": len(today_programming_tasks)
    }

@router.get("/", response_model=OrderPageOut)
def get_orders(
    status: Optional[OrderStatus] = Query(None, description="Filtrar por status"),
    lote: int = Query(None, description="Filtrar por lote"),
    code: str = Query(None, description="Filtrar por código"),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir (paginación)"),
    limit: int = Query(10, ge=1, le=100, description="Cuántos registros devolver (paginación)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PLANNER, UserRole.SUPERVISOR))
):
    query = db.query(order_model.Order)
    if status:
        query = query.filter(order_model.Order.status == status)
    if lote:
        query = query.filter(order_model.Order.lote == lote)
    if code:
        query = query.filter(order_model.Order.code == code)
    total = query.count()
    orders = query.offset(skip).limit(limit).all()
    
    # Serializar las órdenes usando el esquema OrderOut
    serialized_orders = []
    for order in orders:
        order_dict = {
            "lote": order.lote,
            "code": order.code,
            "status": order.status,
            "description": order.description,
            "quantity": order.quantity,
            "bin": order.bin,
            "dueDate": order.dueDate
        }
        serialized_orders.append(order_dict)
    
    return {"orders": serialized_orders, "total": total}

@router.get("/test-sync/{order_id}")
def test_sync_order_status(
    order_id: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Endpoint de prueba para sincronizar el estado de una orden.
    """
    from app.utils.order_status_service import OrderStatusService
    
    try:
        lote_int = int(order_id)
        
        # Obtener la orden antes de sincronizar
        order_before = db.query(order_model.Order).filter(order_model.Order.lote == lote_int).first()
        if not order_before:
            raise HTTPException(status_code=404, detail="Order not found")
        
        status_before = order_before.status
        
        # Sincronizar el estado
        OrderStatusService.sync_order_status_for_lote(db, str(lote_int))
        
        # Obtener la orden después de sincronizar
        order_after = db.query(order_model.Order).filter(order_model.Order.lote == lote_int).first()
        status_after = order_after.status
        
        return {
            "success": True,
            "order_id": order_id,
            "status_before": status_before.value if hasattr(status_before, 'value') else str(status_before),
            "status_after": status_after.value if hasattr(status_after, 'value') else str(status_after),
            "changed": status_before != status_after,
            "order": {
                "lote": order_after.lote,
                "code": order_after.code,
                "status": order_after.status,
                "description": order_after.description,
                "quantity": order_after.quantity,
                "bin": order_after.bin,
                "dueDate": order_after.dueDate
            }
        }
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing order: {str(e)}")

@router.post("/extract-data")
def extract_orders_data(
    order_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de órdenes específicas por sus lotes.
    
    Args:
        order_ids: Lista de lotes de las órdenes a extraer
        
    Returns:
        Datos estructurados de las órdenes solicitadas
    """
    from app.core.task_config import extract_created_orders_data, get_orders_summary, extract_order_data_for_processing
    
    try:
        # Buscar las órdenes en la base de datos
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(order_ids)).all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="No se encontraron órdenes con los lotes especificados")
        
        print(f"[DEBUG] extract_orders_data: Procesando {len(orders)} órdenes encontradas")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(orders)
        summary = get_orders_summary(orders)
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "requested_lotes": order_ids,
            "found_lotes": [order.lote for order in orders],
            "missing_lotes": list(set(order_ids) - set([order.lote for order in orders]))
        }
        
        print(f"[DEBUG] extract_orders_data: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo datos de órdenes: {str(e)}")

@router.get("/extract-recent")
def extract_recent_orders_data(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de órdenes a extraer"),
    status: Optional[OrderStatus] = Query(None, description="Filtrar por status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de las órdenes más recientes.
    
    Args:
        limit: Número máximo de órdenes a extraer
        status: Filtro opcional por status de la orden
        
    Returns:
        Datos estructurados de las órdenes más recientes
    """
    from app.core.task_config import extract_created_orders_data, get_orders_summary
    
    try:
        query = db.query(order_model.Order)
        
        if status:
            query = query.filter(order_model.Order.status == status)
        
        # Ordenar por lote (asumiendo que lotes más altos son más recientes)
        recent_orders = query.order_by(order_model.Order.lote.desc()).limit(limit).all()
        
        if not recent_orders:
            return {
                "extracted_orders": [],
                "summary": get_orders_summary([]),
                "message": "No se encontraron órdenes recientes"
            }
        
        print(f"[DEBUG] extract_recent_orders_data: Procesando {len(recent_orders)} órdenes recientes")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(recent_orders)
        summary = get_orders_summary(recent_orders)
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "limit": limit,
            "status_filter": status.value if status else None,
            "message": f"Se extrajeron {len(recent_orders)} órdenes recientes"
        }
        
        print(f"[DEBUG] extract_recent_orders_data: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes recientes: {str(e)}")

@router.post("/extract-with-activities")
def extract_orders_with_activities(
    order_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de órdenes específicas y obtiene las actividades para cada código.
    
    Args:
        order_ids: Lista de lotes de las órdenes a extraer
        
    Returns:
        Datos de las órdenes con sus actividades correspondientes
    """
    try:
        print(f"[DEBUG] extract_orders_with_activities: Procesando {len(order_ids)} órdenes")
        
        # Buscar las órdenes en la base de datos
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(order_ids)).all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="No se encontraron órdenes con los lotes especificados")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(orders)
        summary = get_orders_summary(orders)
        
        # Obtener actividades para los códigos de las órdenes extraídas
        weighing_service, _ = get_task_services()
        activities_data = weighing_service.get_activities_for_orders(extracted_orders, db)
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "activities_data": activities_data,
            "requested_lotes": order_ids,
            "found_lotes": [order.lote for order in orders],
            "missing_lotes": list(set(order_ids) - set([order.lote for order in orders]))
        }
        
        print(f"[DEBUG] extract_orders_with_activities: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes con actividades: {str(e)}")

@router.get("/extract-recent-with-activities")
def extract_recent_orders_with_activities(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de órdenes a extraer"),
    status: Optional[OrderStatus] = Query(None, description="Filtro opcional por status de la orden"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de las órdenes más recientes y obtiene las actividades para cada código.
    
    Args:
        limit: Número máximo de órdenes a extraer
        status: Filtro opcional por status de la orden
        
    Returns:
        Datos de las órdenes recientes con sus actividades correspondientes
    """
    try:
        query = db.query(order_model.Order)
        
        if status:
            query = query.filter(order_model.Order.status == status)
        
        # Ordenar por lote (asumiendo que lotes más altos son más recientes)
        recent_orders = query.order_by(order_model.Order.lote.desc()).limit(limit).all()
        
        if not recent_orders:
            return {
                "extracted_orders": [],
                "summary": get_orders_summary([]),
                "activities_data": {"activities_by_code": {}, "total_codes_processed": 0, "codes_processed": []},
                "message": "No se encontraron órdenes recientes"
            }
        
        print(f"[DEBUG] extract_recent_orders_with_activities: Procesando {len(recent_orders)} órdenes recientes")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(recent_orders)
        summary = get_orders_summary(recent_orders)
        
        # Obtener actividades para los códigos de las órdenes extraídas
        weighing_service, _ = get_task_services()
        activities_data = weighing_service.get_activities_for_orders(extracted_orders, db)
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "activities_data": activities_data,
            "limit": limit,
            "status_filter": status.value if status else None,
            "message": f"Se extrajeron {len(recent_orders)} órdenes recientes con sus actividades"
        }
        
        print(f"[DEBUG] extract_recent_orders_with_activities: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes recientes con actividades: {str(e)}")

@router.post("/extract-with-weighing-activities")
def extract_orders_with_weighing_activities(
    request: dict = Body(..., description="IDs de las órdenes a procesar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de órdenes específicas y obtiene las actividades de pesado para cada código.
    
    Args:
        request: Diccionario con order_ids (lista de lotes)
        
    Returns:
        Datos de las órdenes con sus actividades de pesado correspondientes
    """
    try:
        order_ids = request.get("order_ids", [])
        if not order_ids:
            raise HTTPException(status_code=400, detail="Se requiere al menos un order_id")
        
        print(f"[DEBUG] extract_orders_with_weighing_activities: Procesando {len(order_ids)} órdenes")
        
        # Buscar las órdenes en la base de datos
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(order_ids)).all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="No se encontraron órdenes con los lotes especificados")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(orders)
        summary = get_orders_summary(orders)
        
        # Obtener actividades de pesado para los códigos de las órdenes extraídas
        weighing_service, _ = get_task_services()
        all_activities = weighing_service.get_activities_for_orders(extracted_orders, db)
        weighing_activities = weighing_service.filter_activities(all_activities)
        weighing_activities_data = {
            "all_activities": all_activities,
            "weighing_activities": weighing_activities,
            "total_orders_processed": len(extracted_orders)
        }
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "weighing_activities_data": weighing_activities_data,
            "requested_lotes": order_ids,
            "found_lotes": [order.lote for order in orders],
            "missing_lotes": list(set(order_ids) - set([order.lote for order in orders])),
            "message": f"Se extrajeron {len(orders)} órdenes con sus actividades de pesado"
        }
        
        print(f"[DEBUG] extract_orders_with_weighing_activities: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes con actividades de pesado: {str(e)}")

@router.get("/extract-recent-with-weighing-activities")
def extract_recent_orders_with_weighing_activities(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de órdenes a extraer"),
    status: Optional[OrderStatus] = Query(None, description="Filtro opcional por status de la orden"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de las órdenes más recientes y obtiene las actividades de pesado para cada código.
    
    Args:
        limit: Número máximo de órdenes a extraer
        status: Filtro opcional por status de la orden
        
    Returns:
        Datos de las órdenes recientes con sus actividades de pesado correspondientes
    """
    try:
        query = db.query(order_model.Order)
        
        if status:
            query = query.filter(order_model.Order.status == status)
        
        # Ordenar por lote (asumiendo que lotes más altos son más recientes)
        recent_orders = query.order_by(order_model.Order.lote.desc()).limit(limit).all()
        
        if not recent_orders:
            return {
                "extracted_orders": [],
                "summary": get_orders_summary([]),
                "weighing_activities_data": {
                    "all_activities": {"activities_by_code": {}, "total_codes_processed": 0, "codes_processed": []},
                    "weighing_activities": {"weighing_activities_by_code": {}, "total_codes_with_weighing": 0, "codes_with_weighing": []},
                    "total_orders_processed": 0
                },
                "message": "No se encontraron órdenes recientes"
            }
        
        print(f"[DEBUG] extract_recent_orders_with_weighing_activities: Procesando {len(recent_orders)} órdenes recientes")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(recent_orders)
        summary = get_orders_summary(recent_orders)
        
        # Obtener actividades de pesado para los códigos de las órdenes extraídas
        weighing_service, _ = get_task_services()
        all_activities = weighing_service.get_activities_for_orders(extracted_orders, db)
        weighing_activities = weighing_service.filter_activities(all_activities)
        weighing_activities_data = {
            "all_activities": all_activities,
            "weighing_activities": weighing_activities,
            "total_orders_processed": len(extracted_orders)
        }
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "weighing_activities_data": weighing_activities_data,
            "limit": limit,
            "status_filter": status.value if status else None,
            "message": f"Se extrajeron {len(recent_orders)} órdenes recientes con sus actividades de pesado"
        }
        
        print(f"[DEBUG] extract_recent_orders_with_weighing_activities: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes recientes con actividades de pesado: {str(e)}")

@router.post("/extract-with-weighing-activities-details")
def extract_orders_with_weighing_activities_details(
    request: dict = Body(..., description="IDs de las órdenes a procesar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de órdenes específicas y obtiene las actividades de pesado con sus detalles específicos.
    
    Args:
        request: Diccionario con order_ids (lista de lotes)
        
    Returns:
        Datos de las órdenes con sus actividades de pesado y detalles específicos
    """
    try:
        order_ids = request.get("order_ids", [])
        if not order_ids:
            raise HTTPException(status_code=400, detail="Se requiere al menos un order_id")
        
        print(f"[DEBUG] extract_orders_with_weighing_activities_details: Procesando {len(order_ids)} órdenes")
        
        # Buscar las órdenes en la base de datos
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(order_ids)).all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="No se encontraron órdenes con los lotes especificados")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(orders)
        summary = get_orders_summary(orders)
        
        # Obtener actividades de pesado con detalles para los códigos de las órdenes extraídas
        weighing_service, _ = get_task_services()
        all_activities = weighing_service.get_activities_for_orders(extracted_orders, db)
        weighing_activities = weighing_service.filter_weighing_activities(all_activities)
        
        # Obtener detalles específicos para cada actividad de pesado
        weighing_activities_with_details = {}
        weighing_activities_by_code = weighing_activities.get("weighing_activities_by_code", {})
        
        for code, code_data in weighing_activities_by_code.items():
            weighing_activities_list = code_data.get("weighing_activities", [])
            activities_with_details = []
            
            for activity_data in weighing_activities_list:
                activity_name = activity_data.get("activity")
                if activity_name:
                    weighing_service, _ = get_task_services()
                    activity_details = weighing_service.get_activity_details_by_code_and_activity(code, activity_name, db)
                    activities_with_details.append({
                        "activity_data": activity_data,
                        "activity_details": activity_details
                    })
            
            if activities_with_details:
                weighing_activities_with_details[code] = {
                    "code": code,
                    "weighing_activities_with_details": activities_with_details,
                    "total_weighing_activities": len(activities_with_details),
                    "found": True
                }
        
        weighing_activities_with_details_data = {
            "all_activities": all_activities,
            "weighing_activities": weighing_activities,
            "weighing_activities_with_details": {
                "weighing_activities_with_details_by_code": weighing_activities_with_details,
                "total_codes_with_weighing_details": len(weighing_activities_with_details),
                "codes_with_weighing_details": list(weighing_activities_with_details.keys())
            },
            "total_orders_processed": len(extracted_orders)
        }
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "weighing_activities_with_details_data": weighing_activities_with_details_data,
            "requested_lotes": order_ids,
            "found_lotes": [order.lote for order in orders],
            "missing_lotes": list(set(order_ids) - set([order.lote for order in orders])),
            "message": f"Se extrajeron {len(orders)} órdenes con sus actividades de pesado y detalles"
        }
        
        print(f"[DEBUG] extract_orders_with_weighing_activities_details: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes con actividades de pesado y detalles: {str(e)}")

@router.get("/extract-recent-with-weighing-activities-details")
def extract_recent_orders_with_weighing_activities_details(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de órdenes a extraer"),
    status: Optional[OrderStatus] = Query(None, description="Filtro opcional por status de la orden"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de las órdenes más recientes y obtiene las actividades de pesado con sus detalles específicos.
    
    Args:
        limit: Número máximo de órdenes a extraer
        status: Filtro opcional por status de la orden
        
    Returns:
        Datos de las órdenes recientes con sus actividades de pesado y detalles específicos
    """
    try:
        query = db.query(order_model.Order)
        
        if status:
            query = query.filter(order_model.Order.status == status)
        
        # Ordenar por lote (asumiendo que lotes más altos son más recientes)
        recent_orders = query.order_by(order_model.Order.lote.desc()).limit(limit).all()
        
        if not recent_orders:
            return {
                "extracted_orders": [],
                "summary": get_orders_summary([]),
                "weighing_activities_with_details_data": {
                    "all_activities": {"activities_by_code": {}, "total_codes_processed": 0, "codes_processed": []},
                    "weighing_activities": {"weighing_activities_by_code": {}, "total_codes_with_weighing": 0, "codes_with_weighing": []},
                    "weighing_activities_with_details": {"weighing_activities_with_details_by_code": {}, "total_codes_with_weighing_details": 0, "codes_with_weighing_details": []},
                    "total_orders_processed": 0
                },
                "message": "No se encontraron órdenes recientes"
            }
        
        print(f"[DEBUG] extract_recent_orders_with_weighing_activities_details: Procesando {len(recent_orders)} órdenes recientes")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(recent_orders)
        summary = get_orders_summary(recent_orders)
        
        # Obtener actividades de pesado con detalles para los códigos de las órdenes extraídas
        weighing_activities_with_details_data = get_weighing_activities_with_details(extracted_orders, db)
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "weighing_activities_with_details_data": weighing_activities_with_details_data,
            "limit": limit,
            "status_filter": status.value if status else None,
            "message": f"Se extrajeron {len(recent_orders)} órdenes recientes con sus actividades de pesado y detalles"
        }
        
        print(f"[DEBUG] extract_recent_orders_with_weighing_activities_details: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes recientes con actividades de pesado y detalles: {str(e)}")

@router.post("/get-activity-details")
def get_activity_details_for_code_and_activity(
    request: dict = Body(..., description="Código y actividad para obtener detalles"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Obtiene los detalles específicos de una actividad basándose en el código y la actividad.
    
    Args:
        request: Diccionario con code y activity
        
    Returns:
        Datos detallados de la actividad específica
    """
    try:
        code = request.get("code")
        activity = request.get("activity")
        
        if not code or not activity:
            raise HTTPException(status_code=400, detail="Se requiere código y actividad")
        
        print(f"[DEBUG] get_activity_details_for_code_and_activity: Obteniendo detalles para código '{code}' y actividad '{activity}'")
        
        # Obtener detalles de la actividad específica
        activity_details = weighing_service.get_activity_details_by_code_and_activity(code, activity, db)
        
        response_data = {
            "request": {"code": code, "activity": activity},
            "result": activity_details,
            "message": f"Detalles obtenidos para código '{code}' y actividad '{activity}'"
        }
        
        print(f"[DEBUG] get_activity_details_for_code_and_activity: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo detalles de actividad: {str(e)}")

@router.post("/calculate-minutes")
def calculate_minutes_for_activity(
    request: dict = Body(..., description="Datos para calcular minutos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Calcula los minutos para una actividad específica basándose en el performance y la cantidad.
    
    Args:
        request: Diccionario con code, activity y order_quantity
        
    Returns:
        Datos de la actividad con minutos calculados
    """
    try:
        code = request.get("code")
        activity = request.get("activity")
        order_quantity = request.get("order_quantity")
        
        if not code or not activity or order_quantity is None:
            raise HTTPException(status_code=400, detail="Se requiere código, actividad y cantidad de la orden")
        
        print(f"[DEBUG] calculate_minutes_for_activity: Calculando minutos para código '{code}', actividad '{activity}', cantidad {order_quantity}")
        
        # Obtener detalles de la actividad con cálculo de minutos
        activity_details_result = weighing_service.get_activity_details_by_code_and_activity(code, activity, db)
        
        if not activity_details_result.get("success", False):
            activity_details_with_minutes = activity_details_result
        else:
            activity_details = activity_details_result.get("activity_details", {})
            performance = activity_details.get("performance")
            
            # Calcular minutos
            weighing_service, _ = get_task_services()
            calculated_minutes = weighing_service.calculate_minutes_from_performance_and_quantity(performance, order_quantity)
            
            # Calcular horas para mostrar en la fórmula
            hours_calculation = performance * order_quantity
            
            activity_details_with_minutes = {
                "success": True,
                "code": code,
                "activity": activity,
                "order_quantity": order_quantity,
                "activity_details": activity_details,
                "minutes_calculation": {
                    "performance": performance,
                    "quantity": order_quantity,
                    "hours_calculation": hours_calculation,
                    "calculated_minutes": calculated_minutes,
                    "formula": f"{performance} horas * {order_quantity} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
                },
                "message": f"Datos obtenidos y minutos calculados para código '{code}' y actividad '{activity}'"
            }
        
        response_data = {
            "request": {"code": code, "activity": activity, "order_quantity": order_quantity},
            "result": activity_details_with_minutes,
            "message": f"Minutos calculados para código '{code}' y actividad '{activity}'"
        }
        
        print(f"[DEBUG] calculate_minutes_for_activity: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando minutos: {str(e)}")

@router.post("/extract-with-weighing-activities-minutes")
def extract_orders_with_weighing_activities_minutes(
    request: dict = Body(..., description="IDs de las órdenes a procesar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de órdenes específicas y obtiene las actividades de pesado con minutos calculados.
    
    Args:
        request: Diccionario con order_ids (lista de lotes)
        
    Returns:
        Datos de las órdenes con sus actividades de pesado y minutos calculados
    """
    try:
        order_ids = request.get("order_ids", [])
        if not order_ids:
            raise HTTPException(status_code=400, detail="Se requiere al menos un order_id")
        
        print(f"[DEBUG] extract_orders_with_weighing_activities_minutes: Procesando {len(order_ids)} órdenes")
        
        # Buscar las órdenes en la base de datos
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(order_ids)).all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="No se encontraron órdenes con los lotes especificados")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(orders)
        summary = get_orders_summary(orders)
        
        # Obtener actividades de pesado con minutos calculados para los códigos de las órdenes extraídas
        weighing_service, _ = get_task_services()
        weighing_activities_with_minutes_data = weighing_service.get_weighing_activities_with_minutes(extracted_orders, db)
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "weighing_activities_with_minutes_data": weighing_activities_with_minutes_data,
            "requested_lotes": order_ids,
            "found_lotes": [order.lote for order in orders],
            "missing_lotes": list(set(order_ids) - set([order.lote for order in orders])),
            "message": f"Se extrajeron {len(orders)} órdenes con sus actividades de pesado y minutos calculados"
        }
        
        print(f"[DEBUG] extract_orders_with_weighing_activities_minutes: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes con actividades de pesado y minutos: {str(e)}")

@router.get("/extract-recent-with-weighing-activities-minutes")
def extract_recent_orders_with_weighing_activities_minutes(
    limit: int = Query(10, ge=1, le=100, description="Número máximo de órdenes a extraer"),
    status: Optional[OrderStatus] = Query(None, description="Filtro opcional por status de la orden"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Extrae datos de las órdenes más recientes y obtiene las actividades de pesado con minutos calculados.
    
    Args:
        limit: Número máximo de órdenes a extraer
        status: Filtro opcional por status de la orden
        
    Returns:
        Datos de las órdenes recientes con sus actividades de pesado y minutos calculados
    """
    try:
        query = db.query(order_model.Order)
        
        if status:
            query = query.filter(order_model.Order.status == status)
        
        # Ordenar por lote (asumiendo que lotes más altos son más recientes)
        recent_orders = query.order_by(order_model.Order.lote.desc()).limit(limit).all()
        
        if not recent_orders:
            return {
                "extracted_orders": [],
                "summary": get_orders_summary([]),
                "weighing_activities_with_minutes_data": {
                    "all_activities": {"activities_by_code": {}, "total_codes_processed": 0, "codes_processed": []},
                    "weighing_activities": {"weighing_activities_by_code": {}, "total_codes_with_weighing": 0, "codes_with_weighing": []},
                    "weighing_activities_with_details": {"weighing_activities_with_details_by_code": {}, "total_codes_with_weighing_details": 0, "codes_with_weighing_details": []},
                    "weighing_activities_with_minutes": {"weighing_activities_with_minutes_by_code": {}, "total_codes_with_weighing_minutes": 0, "codes_with_weighing_minutes": []},
                    "total_orders_processed": 0
                },
                "message": "No se encontraron órdenes recientes"
            }
        
        print(f"[DEBUG] extract_recent_orders_with_weighing_activities_minutes: Procesando {len(recent_orders)} órdenes recientes")
        
        # Extraer solo lote, quantity y code usando las funciones utilitarias
        extracted_orders = extract_created_orders_data(recent_orders)
        summary = get_orders_summary(recent_orders)
        
        # Obtener actividades de pesado con minutos calculados para los códigos de las órdenes extraídas
        weighing_activities_with_minutes_data = weighing_service.get_weighing_activities_with_minutes(extracted_orders, db)
        
        response_data = {
            "extracted_orders": extracted_orders,
            "summary": summary,
            "weighing_activities_with_minutes_data": weighing_activities_with_minutes_data,
            "limit": limit,
            "status_filter": status.value if status else None,
            "message": f"Se extrajeron {len(recent_orders)} órdenes recientes con sus actividades de pesado y minutos calculados"
        }
        
        print(f"[DEBUG] extract_recent_orders_with_weighing_activities_minutes: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes recientes con actividades de pesado y minutos: {str(e)}")

@router.post("/calculate-simple-minutes")
def calculate_simple_minutes(
    request: dict = Body(..., description="Performance y cantidad para calcular minutos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Calcula los minutos simplemente multiplicando performance con cantidad.
    
    Args:
        request: Diccionario con performance y quantity
        
    Returns:
        Minutos calculados
    """
    try:
        performance = request.get("performance")
        quantity = request.get("quantity")
        
        if performance is None or quantity is None:
            raise HTTPException(status_code=400, detail="Se requiere performance y quantity")
        
        print(f"[DEBUG] calculate_simple_minutes: Calculando minutos - performance={performance}, quantity={quantity}")
        
        # Calcular minutos
        calculated_minutes = weighing_service.calculate_minutes_from_performance_and_quantity(performance, quantity)
        
        # Calcular horas para mostrar en la fórmula
        hours_calculation = performance * quantity
        
        response_data = {
            "request": {"performance": performance, "quantity": quantity},
            "result": {
                "performance": performance,
                "quantity": quantity,
                "hours_calculation": hours_calculation,
                "calculated_minutes": calculated_minutes,
                "formula": f"{performance} horas * {quantity} = {hours_calculation} horas * 60 = {calculated_minutes} minutos (con ceiling)"
            },
            "message": f"Minutos calculados: {calculated_minutes}"
        }
        
        print(f"[DEBUG] calculate_simple_minutes: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando minutos simples: {str(e)}")


@router.get("/weighing/most-suitable-team")
def get_most_suitable_weighing_team_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Obtiene el equipo más idóneo para actividades de pesado.
    
    Returns:
        Información del equipo más idóneo para pesado con ID y nombre
    """
    try:
        print(f"[DEBUG] get_most_suitable_weighing_team_endpoint: Iniciando búsqueda de equipo más idóneo para pesado")
        
        weighing_service, _ = get_task_services()
        result = weighing_service.get_most_suitable_weighing_team(db)
        
        print(f"[DEBUG] get_most_suitable_weighing_team_endpoint: Resultado obtenido - {result}")
        
        return result
        
    except Exception as e:
        print(f"[DEBUG] get_most_suitable_weighing_team_endpoint: Error - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo equipo más idóneo para pesado: {str(e)}")


@router.get("/weighing/most-suitable-team-with-programmings")
def get_most_suitable_weighing_team_with_programmings_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Obtiene el equipo más idóneo para actividades de pesado y sus programaciones disponibles.
    
    Returns:
        Información del equipo más idóneo para pesado con sus programaciones disponibles
    """
    try:
        print(f"[DEBUG] get_most_suitable_weighing_team_with_programmings_endpoint: Iniciando búsqueda de equipo y programaciones")
        
        team_result = weighing_service.get_most_suitable_weighing_team(db)
        
        if not team_result.get("success", False):
            result = {
                "success": False,
                "message": "No se pudo obtener equipo idóneo para pesado",
                "team_data": team_result,
                "available_programmings": []
            }
        else:
            team_id = team_result.get("most_suitable_team", {}).get("id")
            weighing_service, _ = get_task_services()
            available_programmings = weighing_service.get_available_programmings_for_team(team_id, db)
            
            result = {
                "success": True,
                "message": f"Equipo idóneo y programaciones obtenidas exitosamente",
                "team_data": team_result,
                "available_programmings": {
                    "success": True,
                    "message": "Programaciones disponibles obtenidas exitosamente",
                    "team_id": team_id,
                    "team_name": team_result.get("most_suitable_team", {}).get("name"),
                    "programmings": available_programmings,
                    "total_available_programmings": len(available_programmings)
                }
            }
        
        print(f"[DEBUG] get_most_suitable_weighing_team_with_programmings_endpoint: Resultado obtenido - {result}")
        
        return result
        
    except Exception as e:
        print(f"[DEBUG] get_most_suitable_weighing_team_with_programmings_endpoint: Error - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo equipo y programaciones: {str(e)}")


@router.post("/weighing/verify-time-limit")
def verify_programming_time_limit_endpoint(
    request: dict = Body(..., description="Programaciones y minutos de tarea para verificar límite de tiempo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Verifica que al agregar una tarea a una programación no se exceda el límite de tiempo (17:40) más de 5 minutos.
    
    Args:
        request: Diccionario con programmings (lista de programaciones) y task_minutes (minutos de la tarea)
        
    Returns:
        Programación seleccionada que cumple con el límite de tiempo
    """
    try:
        programmings = request.get("programmings")
        task_minutes = request.get("task_minutes")
        
        if not programmings or task_minutes is None:
            raise HTTPException(status_code=400, detail="Se requiere programmings (lista) y task_minutes (entero)")
        
        print(f"[DEBUG] verify_programming_time_limit_endpoint: Verificando límite de tiempo")
        print(f"[DEBUG] verify_programming_time_limit_endpoint: Programaciones: {len(programmings)}")
        print(f"[DEBUG] verify_programming_time_limit_endpoint: Minutos de tarea: {task_minutes}")
        
        weighing_service, _ = get_task_services()
        result = weighing_service.verify_programming_time_limit(programmings, task_minutes, db)
        
        print(f"[DEBUG] verify_programming_time_limit_endpoint: Resultado obtenido - {result}")
        
        return result
        
    except Exception as e:
        print(f"[DEBUG] verify_programming_time_limit_endpoint: Error - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error verificando límite de tiempo: {str(e)}")


@router.post("/weighing/team-with-time-verification")
def get_most_suitable_weighing_team_with_time_verification_endpoint(
    request: dict = Body(..., description="Minutos de la tarea para verificar límite de tiempo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    """
    Obtiene el equipo más idóneo para pesado, sus programaciones disponibles y verifica el límite de tiempo.
    
    Args:
        request: Diccionario con task_minutes (minutos de la tarea)
        
    Returns:
        Equipo, programaciones y verificación de tiempo
    """
    try:
        task_minutes = request.get("task_minutes")
        
        if task_minutes is None:
            raise HTTPException(status_code=400, detail="Se requiere task_minutes (entero)")
        
        print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification_endpoint: Iniciando búsqueda con verificación de tiempo")
        print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification_endpoint: Minutos de tarea: {task_minutes}")
        
        team_result = weighing_service.get_most_suitable_weighing_team(db)
        
        if not team_result.get("success", False):
            result = {
                "success": False,
                "message": "No se pudo obtener equipo idóneo y programaciones",
                "team_data": None,
                "available_programmings": None,
                "time_verification": None
            }
        else:
            team_id = team_result.get("most_suitable_team", {}).get("id")
            available_programmings = weighing_service.get_available_programmings_for_team(team_id, db)
            
            if not available_programmings:
                result = {
                    "success": False,
                    "message": "No hay programaciones disponibles para verificar",
                    "team_data": team_result,
                    "available_programmings": None,
                    "time_verification": None
                }
            else:
                time_verification = weighing_service.verify_programming_time_limit(available_programmings, task_minutes, db)
                
                result = {
                    "success": True,
                    "message": "Equipo idóneo, programaciones y verificación de tiempo obtenidos exitosamente",
                    "team_data": team_result,
                    "available_programmings": {
                        "success": True,
                        "programmings": available_programmings,
                        "total_available_programmings": len(available_programmings)
                    },
                    "time_verification": time_verification
                }
        
        print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification_endpoint: Resultado obtenido - {result}")
        
        return result
        
    except Exception as e:
        print(f"[DEBUG] get_most_suitable_weighing_team_with_time_verification_endpoint: Error - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo equipo con verificación de tiempo: {str(e)}")