"""
Rutas de la API para la gestión de órdenes de producción: creación, actualización de estado, eliminación y consulta con filtros.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate, OrderPageOut, OrderWarehouseUpdate, OrderWarehouseOut
from app.models import order as order_model
from app.db.dependency import get_db
from typing import List, Union, Optional
from app.models.user import User
from app.utils.dependencies import get_current_user, require_roles
from app.models.role import UserRole
from app.models.state import OrderStatus
from app.utils.data_cleaning import clean_order_data
from datetime import datetime

def _get_delivery_status_message(status: OrderStatus, missing_quantity: int) -> str:
    """Genera el mensaje apropiado según el estado y cantidad faltante."""
    if status == OrderStatus.completed:
        if missing_quantity < 0:
            return f"Orden completada con {abs(missing_quantity)} unidades adicionales."
        else:
            return "Orden completada."
    else:
        return f"Cantidad faltante: {missing_quantity}"
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
    auto_create_tasks: bool = Query(True, description="Crear tareas automáticamente"),
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
            status=OrderStatus.unprogrammed,  # Siempre iniciar como unprogrammed
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
    
    # Serializar las órdenes creadas para la respuesta
    serialized_orders = []
    for order in created_orders:
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
    
    response_data = {
        "created_orders": serialized_orders,
        "extracted_orders": extracted_orders,
        "summary": summary,
        "auto_create_tasks": auto_create_tasks
    }
    
    # Solo crear tareas si auto_create_tasks es True
    if auto_create_tasks:
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
        
        response_data.update({
            "activities_data": activities_data,
            "weighing_tasks_result": weighing_tasks_result,
            "fabrication_tasks_result": fabrication_tasks_result,
            "packaging_tasks_result": packaging_tasks_result,
            "message": f"Se crearon {len(created_orders)} órdenes exitosamente. {weighing_tasks_result.get('tasks_created', 0)} tareas de pesado, {fabrication_tasks_result.get('tasks_created', 0)} tareas de fabricación y {packaging_tasks_result.get('tasks_created', 0)} tareas de empaque creadas."
        })
    else:
        response_data.update({
            "message": f"Se crearon {len(created_orders)} órdenes exitosamente. No se crearon tareas automáticamente."
        })
    
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

@router.patch("/{order_id}")
def update_order_warehouse(order_id: str, order_update: OrderWarehouseUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))):
    from app.utils.order_status_service import OrderStatusService
    
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update_data = order_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(db_order, key, value)
    
    # Si se actualizó missing_quantity, verificar cambio de estado
    if 'missing_quantity' in update_data:
        OrderStatusService.update_order_status_based_on_missing_quantity(db, db_order)
    
    db.commit()
    db.refresh(db_order)
    return {
        "lote": db_order.lote,
        "received_user": db_order.received_user,
        "received_date": db_order.received_date,
        "received_quantity": db_order.received_quantity,
        "missing_quantity": db_order.missing_quantity,
        "submitted_user": db_order.submitted_user,
        "submitted_date": db_order.submitted_date,
        "status": db_order.status
    }

@router.patch("/{order_id}/status")
def update_order_status(order_id: str, status_update: OrderStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))):
    """
    Actualiza manualmente el estado de una orden.
    Todos los roles excepto USER pueden actualizar el estado.
    """
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
        "dueDate": db_order.dueDate,
        "missing_quantity": db_order.missing_quantity
    }
    return order_dict

@router.patch("/{order_id}/warehouse-fields")
def update_order_warehouse_fields(
    order_id: str, 
    order_update: OrderWarehouseUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))
):
    """
    Endpoint específico para actualizar campos de almacén y gestionar el flujo de estados automáticamente.
    Cuando se actualiza missing_quantity, el estado cambia automáticamente según las reglas del negocio.
    """
    from app.utils.order_status_service import OrderStatusService
    
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Guardar el estado anterior para logging
    previous_status = db_order.status
    
    # Actualizar solo los campos que se enviaron
    update_data = order_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            setattr(db_order, key, value)
    
    # Si se actualizó missing_quantity, aplicar la lógica de cambio de estado automático
    if 'missing_quantity' in update_data and update_data['missing_quantity'] is not None:
        OrderStatusService.update_order_status_based_on_missing_quantity(db, db_order)
    
    db.commit()
    db.refresh(db_order)
    
    return {
        "lote": db_order.lote,
        "code": db_order.code,
        "status": db_order.status,
        "previous_status": previous_status,
        "status_changed": previous_status != db_order.status,
        "received_user": db_order.received_user,
        "received_date": db_order.received_date,
        "received_quantity": db_order.received_quantity,
        "missing_quantity": db_order.missing_quantity,
        "submitted_user": db_order.submitted_user,
        "submitted_date": db_order.submitted_date,
        "message": f"Orden actualizada. Estado cambió de {previous_status} a {db_order.status}" if previous_status != db_order.status else "Orden actualizada sin cambio de estado"
    }

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

@router.post("/test_order_flow/{order_lote}")
def test_order_status_flow(
    order_lote: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Endpoint de prueba para verificar el flujo completo de estados de una orden.
    """
    from app.utils.order_status_service import OrderStatusService
    from app.models.task import Task
    
    # Buscar la orden
    order = db.query(order_model.Order).filter(order_model.Order.lote == order_lote).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Buscar tareas asociadas a esta orden
    tasks = db.query(Task).filter(Task.lote == str(order_lote)).all()
    
    # Información de las tareas
    tasks_info = []
    for task in tasks:
        task_info = {
            "id": str(task.id),
            "lote": task.lote,
            "activity": task.activity,
            "code_activity": task.code.activity if task.code else None,
            "description": task.description
        }
        tasks_info.append(task_info)
    
    return {
        "order": {
            "lote": order.lote,
            "code": order.code,
            "status": order.status,
            "description": order.description
        },
        "tasks": tasks_info,
        "tasks_count": len(tasks),
        "message": f"Orden {order_lote} tiene {len(tasks)} tareas asociadas"
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
            "dueDate": order.dueDate,
            "received_user": order.received_user,
            "received_date": order.received_date,
            "received_quantity": order.received_quantity,
            "missing_quantity": order.missing_quantity,
            "submitted_user": order.submitted_user,
            "submitted_date": order.submitted_date
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
            "message": f"Se extrajeron {len(recent_orders)} órdenes recientes con actividades"
        }
        
        print(f"[DEBUG] extract_recent_orders_with_activities: Respuesta final - {response_data}")
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extrayendo órdenes recientes con actividades: {str(e)}")

@router.get("/delivered", response_model=OrderPageOut)
def get_delivered_orders(
    lote: int = Query(None, description="Filtrar por lote"),
    code: str = Query(None, description="Filtrar por código"),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir (paginación)"),
    limit: int = Query(10, ge=1, le=100, description="Cuántos registros devolver (paginación)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    """
    Obtiene órdenes que han sido entregadas pero no completadas.
    Solo muestra órdenes en estado 'delivered' que están pendientes de recepción en almacén.
    Solo accesible para admin, supervisor y warehouse (recepción).
    """
    from sqlalchemy import or_
    
    query = db.query(order_model.Order).filter(
        order_model.Order.status == OrderStatus.delivered  # Órdenes entregadas pero no completadas
    )
    
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
            "dueDate": order.dueDate,
            "received_user": order.received_user,
            "received_date": order.received_date,
            "received_quantity": order.received_quantity,
            "missing_quantity": order.missing_quantity,
            "submitted_user": order.submitted_user,
            "submitted_date": order.submitted_date
        }
        serialized_orders.append(order_dict)
    
    return {"orders": serialized_orders, "total": total}

@router.post("/{order_id}/receive")
def receive_order(
    order_id: str,
    request_data: dict = Body(default={}),
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    """
    Marca una orden como recibida completamente por el usuario actual.
    Automáticamente recibe la cantidad entregada y cambia el estado a completed.
    Solo accesible para admin, supervisor y warehouse (recepción).
    """
    from datetime import date
    
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verificar que la orden haya sido entregada
    if db_order.status != OrderStatus.delivered:
        raise HTTPException(status_code=400, detail="La orden debe estar en estado 'entregado' para poder ser recibida")
    
    # Verificar que no esté ya completada
    if db_order.status == OrderStatus.completed:
        raise HTTPException(status_code=400, detail="La orden ya está completada")
    
    # Marcar como recibida automáticamente con la cantidad entregada
    db_order.received_user = current_user.username
    db_order.received_date = date.today()
    # No cambiar received_quantity ya que se estableció en la entrega

    # Determinar el estado final: si se pasa custom_status lo respetamos,
    # sino inferimos a partir de missing_quantity:
    # - if missing_quantity > 0 -> pending
    # - else -> completed
    custom_status = request_data.get("custom_status")
    if custom_status:
        if custom_status == "pending":
            db_order.status = OrderStatus.pending
            status_message = "pendiente (requiere revisión)"
        else:
            db_order.status = OrderStatus.completed
            status_message = "completada"
    else:
        # Inferir por cantidad faltante
        try:
            current_missing = db_order.missing_quantity if db_order.missing_quantity is not None else 0
            if current_missing > 0:
                db_order.status = OrderStatus.pending
                status_message = "pendiente (quedan faltantes)"
            else:
                db_order.status = OrderStatus.completed
                status_message = "completada"
        except Exception:
            # Fallback por defecto a completed
            db_order.status = OrderStatus.completed
            status_message = "completada"
    
    db.commit()
    db.refresh(db_order)
    
    return {
        "message": f"Orden {order_id} recibida exitosamente por {current_user.username} - Estado: {status_message}",
        "lote": db_order.lote,
        "status": db_order.status,
        "received_user": db_order.received_user,
        "received_date": db_order.received_date,
        "received_quantity": db_order.received_quantity,
        "missing_quantity": db_order.missing_quantity,
        "status": db_order.status,
        "status_message": status_message
    }

@router.get("/manufactured")
def get_manufactured_orders(
    skip: int = Query(0, ge=0, description="Cuántos registros omitir (paginación)"),
    limit: int = Query(10, ge=1, le=100, description="Cuántos registros devolver (paginación)"),
    lote: Optional[int] = Query(None, description="Filtrar por lote"),
    code: Optional[str] = Query(None, description="Filtrar por código"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    """
    Obtiene todas las órdenes con estado 'manufactured' y 'pending' que están listas para entregar.
    Accesible para roles admin, planner, supervisor y warehouse.
    """
    from sqlalchemy import or_
    
    # Buscar órdenes manufacturadas y pendientes que están listas para entregar
    # Incluir órdenes con estado manufactured o pending
    query = db.query(order_model.Order).filter(
        or_(
            order_model.Order.status == OrderStatus.manufactured,
            order_model.Order.status == OrderStatus.pending
        )
    )
    
    if lote:
        query = query.filter(order_model.Order.lote == lote)
    if code:
        query = query.filter(order_model.Order.code.ilike(f"%{code}%"))
    
    total = query.count()
    orders = query.offset(skip).limit(limit).all()
    
    # Serializar las órdenes
    serialized_orders = []
    for order in orders:
        order_dict = {
            "lote": order.lote,
            "code": order.code,
            "status": order.status,
            "description": order.description,
            "quantity": order.quantity,
            "bin": order.bin,
            "dueDate": order.dueDate,
            "received_user": order.received_user,
            "received_date": order.received_date,
            "received_quantity": order.received_quantity or 0,
            "missing_quantity": order.missing_quantity or order.quantity,
            "submitted_user": order.submitted_user,
            "submitted_date": order.submitted_date
        }
        serialized_orders.append(order_dict)
    
    return {"orders": serialized_orders, "total": total}

@router.post("/{order_id}/deliver")
def deliver_order(
    order_id: str,
    delivery_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Realiza la entrega de una orden manufacturada o pendiente.
    Solo para roles admin, planner y supervisor.
    """
    from datetime import date
    
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if db_order.status not in [OrderStatus.manufactured, OrderStatus.pending]:
        raise HTTPException(status_code=400, detail="Order must be in manufactured or pending status to be delivered")
    
    delivered_quantity = delivery_data.get("delivered_quantity")
    if delivered_quantity is None or delivered_quantity < 0:
        # Allow 0 delivered (explicit), but reject negative or missing values
        raise HTTPException(status_code=400, detail="Delivered quantity must be >= 0")
    
    # Calcular cantidad recibida total y faltante
    current_received = db_order.received_quantity or 0
    new_received_total = current_received + delivered_quantity
    new_missing_quantity = db_order.quantity - new_received_total
    
    # Actualizar campos de entrega
    db_order.submitted_user = current_user.username
    db_order.submitted_date = date.today()
    db_order.received_quantity = new_received_total
    db_order.missing_quantity = new_missing_quantity  # Puede ser negativo para indicar exceso
    
    # Cambiar estado a delivered (independientemente de la cantidad)
    # El estado solo cambiará a completed cuando se reciba en almacén
    db_order.status = OrderStatus.delivered
    
    db.commit()
    db.refresh(db_order)
    
    return {
        "lote": db_order.lote,
        "code": db_order.code,
        "status": db_order.status,
        "quantity": db_order.quantity,
        "received_quantity": db_order.received_quantity,
        "missing_quantity": db_order.missing_quantity,
        "delivered_quantity": delivered_quantity,
        "difference": abs(new_missing_quantity),
        "submitted_user": db_order.submitted_user,
        "submitted_date": db_order.submitted_date,
        "message": f"Entrega realizada exitosamente. {_get_delivery_status_message(db_order.status, db_order.missing_quantity)}"
    }

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
        raise HTTPException(status_code=500, detail=f"Error obteniendo equipo con verificación de tiempo: {str(e)}")

@router.post("/test_packaging_completion/{order_lote}")
def test_packaging_task_completion(
    order_lote: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Endpoint de prueba para simular la completación de una tarea de empaque y verificar el cambio de estado.
    """
    from app.utils.order_status_service import OrderStatusService
    from app.models.task import Task
    from app.models.programming import ProgrammingTask
    
    # Buscar la orden
    order = db.query(order_model.Order).filter(order_model.Order.lote == order_lote).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Buscar tareas de empaque asociadas a esta orden
    packaging_tasks = db.query(Task).filter(
        Task.lote == str(order_lote)
    ).all()
    
    packaging_task = None
    for task in packaging_tasks:
        # Verificar si es una tarea de empaque
        if task.code and task.code.activity:
            activity = task.code.activity.lower().strip()
            if ('empaque' in activity or 'empacado' in activity or 'packaging' in activity):
                packaging_task = task
                break
        elif task.activity:
            activity = task.activity.lower().strip()
            if ('empaque' in activity or 'empacado' in activity or 'packaging' in activity):
                packaging_task = task
                break
    
    if not packaging_task:
        return {
            "error": "No se encontró tarea de empaque para esta orden",
            "order_lote": order_lote,
            "available_tasks": [
                {
                    "id": str(t.id),
                    "activity": t.activity,
                    "code_activity": t.code.activity if t.code else None
                } for t in packaging_tasks
            ]
        }
    
    # Buscar la ProgrammingTask asociada
    programming_task = db.query(ProgrammingTask).filter(
        ProgrammingTask.task_id == packaging_task.id
    ).first()
    
    if not programming_task:
        return {
            "error": "No se encontró programming task para la tarea de empaque",
            "packaging_task_id": str(packaging_task.id)
        }
    
    # Guardar estado anterior
    previous_status = order.status
    
    # Marcar la tarea como completada
    programming_task.is_completed = True
    programming_task.completed_by_user_id = current_user.id
    db.commit()
    
    # Llamar al servicio para actualizar el estado de la orden
    OrderStatusService.update_order_status_for_task_completion(db, programming_task)
    
    # Refrescar la orden para ver los cambios
    db.refresh(order)
    
    return {
        "success": True,
        "order_lote": order_lote,
        "previous_status": previous_status,
        "new_status": order.status,
        "status_changed": previous_status != order.status,
        "packaging_task": {
            "id": str(packaging_task.id),
            "activity": packaging_task.activity,
            "code_activity": packaging_task.code.activity if packaging_task.code else None,
            "is_completed": programming_task.is_completed
        },
        "message": f"Tarea de empaque marcada como completada. Estado cambió de {previous_status} a {order.status}" if previous_status != order.status else f"Tarea completada pero estado no cambió (sigue en {order.status})"
    }

@router.get("/debug/database_connection")
def debug_database_connection(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Endpoint de diagnóstico para verificar la conexión a la base de datos.
    """
    try:
        # Probar una consulta simple
        result = db.execute("SELECT 1 as test").fetchone()
        
        # Contar órdenes
        orders_count = db.query(order_model.Order).count()
        
        return {
            "database_connection": "OK",
            "test_query": result[0] if result else None,
            "orders_count": orders_count,
            "message": "Base de datos funcionando correctamente"
        }
    except Exception as e:
        return {
            "database_connection": "ERROR",
            "error": str(e),
            "message": "Error en la conexión a la base de datos"
        }

@router.post("/debug/test_order_update/{order_lote}")
def debug_test_order_update(
    order_lote: int,
    new_status: OrderStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Endpoint de diagnóstico para probar la actualización de estado de una orden específica.
    """
    try:
        # Buscar la orden
        order = db.query(order_model.Order).filter(order_model.Order.lote == order_lote).first()
        if not order:
            return {
                "success": False,
                "error": "Order not found",
                "order_lote": order_lote
            }
        
        # Guardar estado anterior
        previous_status = order.status
        
        # Intentar actualizar el estado
        order.status = new_status
        db.commit()
        
        # Verificar que se actualizó
        db.refresh(order)
        
        return {
            "success": True,
            "order_lote": order_lote,
            "previous_status": previous_status,
            "new_status": order.status,
            "status_changed": previous_status != order.status,
            "message": f"Estado actualizado de {previous_status} a {order.status}"
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "order_lote": order_lote,
            "message": "Error actualizando el estado de la orden"
        }

@router.post("/debug/complete_packaging_task")
def debug_complete_packaging_task(
    order_lote: int = Body(...),
    task_id: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Endpoint de diagnóstico para completar manualmente una tarea de empaque específica.
    """
    from app.utils.order_status_service import OrderStatusService
    from app.models.task import Task
    from app.models.programming import ProgrammingTask
    
    try:
        # Buscar la orden
        order = db.query(order_model.Order).filter(order_model.Order.lote == order_lote).first()
        if not order:
            return {
                "success": False,
                "error": "Order not found",
                "order_lote": order_lote
            }
        
        # Buscar la tarea
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {
                "success": False,
                "error": "Task not found",
                "task_id": task_id
            }
        
        # Buscar la ProgrammingTask
        programming_task = db.query(ProgrammingTask).filter(
            ProgrammingTask.task_id == task_id
        ).first()
        
        if not programming_task:
            return {
                "success": False,
                "error": "Programming task not found",
                "task_id": task_id
            }
        
        # Información antes del cambio
        previous_status = order.status
        previous_completed = programming_task.is_completed
        
        # Marcar como completada
        programming_task.is_completed = True
        programming_task.completed_by_user_id = current_user.id
        db.commit()
        
        # Llamar al servicio
        OrderStatusService.update_order_status_for_task_completion(db, programming_task)
        
        # Refrescar para ver cambios
        db.refresh(order)
        db.refresh(programming_task)
        
        return {
            "success": True,
            "order_lote": order_lote,
            "task_id": task_id,
            "task_info": {
                "lote": task.lote,
                "activity": task.activity,
                "code_activity": task.code.activity if task.code else None,
                "description": task.description
            },
            "previous_status": previous_status,
            "new_status": order.status,
            "status_changed": previous_status != order.status,
            "task_completed": programming_task.is_completed,
            "message": f"Tarea completada. Estado cambió de {previous_status} a {order.status}" if previous_status != order.status else f"Tarea completada pero estado no cambió (sigue en {order.status})"
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "order_lote": order_lote,
            "task_id": task_id,
            "message": "Error completando la tarea"
        }
@router.get("/surplus", response_model=OrderPageOut)
def get_surplus_orders(
    lote: int = Query(None, description="Filtrar por lote"),
    code: str = Query(None, description="Filtrar por código"),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir (paginación)"),
    limit: int = Query(10, ge=1, le=100, description="Cuántos registros devolver (paginación)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Obtiene órdenes que tienen sobrantes (cantidad entregada mayor a la original).
    Busca en órdenes manufacturadas, entregadas y completadas con missing_quantity negativo.
    Solo accesible para admin, planner y supervisor.
    """
    
    from sqlalchemy import and_, or_
    
    query = db.query(order_model.Order).filter(
        or_(
            and_(
                order_model.Order.status == OrderStatus.manufactured,
                order_model.Order.missing_quantity < 0  # Con sobrantes (negativo indica exceso)
            ),
            and_(
                order_model.Order.status == OrderStatus.delivered,
                order_model.Order.missing_quantity < 0  # Con sobrantes (negativo indica exceso)
            ),
            and_(
                order_model.Order.status == OrderStatus.completed,
                order_model.Order.missing_quantity < 0  # Con sobrantes (negativo indica exceso)
            )
        )
    )
    
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
            "dueDate": order.dueDate,
            "received_user": order.received_user,
            "received_date": order.received_date,
            "received_quantity": order.received_quantity,
            "missing_quantity": order.missing_quantity,
            "submitted_user": order.submitted_user,
            "submitted_date": order.submitted_date
        }
        serialized_orders.append(order_dict)
    
    return {"orders": serialized_orders, "total": total}

@router.get("/available-for-transfer/{code}")
def get_available_orders_for_transfer(
    code: str,
    exclude_lote: Optional[int] = Query(None, description="Lote a excluir de los resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Obtiene órdenes disponibles para recibir transferencia de sobrantes.
    Busca órdenes del mismo código que no estén completadas y tengan cantidad faltante.
    """
    
    # Normalizar el código base (parte antes de '-') y buscar por prefijo
    code_base = code.split('-')[0].strip()

    query = db.query(order_model.Order).filter(
        order_model.Order.code.ilike(f"{code_base}%"),
        order_model.Order.status.in_([OrderStatus.unprogrammed, OrderStatus.programmed, OrderStatus.manufactured]),
        order_model.Order.missing_quantity >= 0  # Sin sobrantes o con faltantes
    )

    if exclude_lote:
        query = query.filter(order_model.Order.lote != exclude_lote)

    available_orders = query.all()

    # Si no encontramos candidatos con la consulta estricta, intentar una búsqueda más laxa
    if not available_orders:
        try:
            print(f"[DEBUG] No candidates with strict filters for code_base={code_base}, trying relaxed query...")
            relaxed_query = db.query(order_model.Order).filter(
                order_model.Order.code.ilike(f"{code_base}%")
            )
            if exclude_lote:
                relaxed_query = relaxed_query.filter(order_model.Order.lote != exclude_lote)
            relaxed_orders = relaxed_query.all()
            print(f"[DEBUG] relaxed query found={len(relaxed_orders)}")
            for ao in relaxed_orders:
                print(f"[DEBUG] relaxed candidate lote={ao.lote} code={ao.code} missing={ao.missing_quantity} status={ao.status}")
            # Use relaxed result for response so frontend can inspect
            available_orders = relaxed_orders
        except Exception as e:
            print("[DEBUG] error during relaxed query:", e)

    # DEBUG: imprimir información útil para depuración
    try:
        print(f"[DEBUG] available-for-transfer: code_base={code_base} exclude_lote={exclude_lote} -> found={len(available_orders)}")
        for ao in available_orders:
            print(f"[DEBUG] candidate lote={ao.lote} code={ao.code} missing={ao.missing_quantity} status={ao.status}")
    except Exception as e:
        print("[DEBUG] error printing available_orders:", e)
    
    # Serializar las órdenes disponibles
    serialized_orders = []
    for order in available_orders:
        order_dict = {
            "lote": order.lote,
            "code": order.code,
            "status": order.status,
            "description": order.description,
            "quantity": order.quantity,
            "missing_quantity": order.missing_quantity,
            "dueDate": order.dueDate
        }
        serialized_orders.append(order_dict)
    
    return {"available_orders": serialized_orders}

@router.post("/{source_lote}/transfer-surplus")
def transfer_surplus_to_order(
    source_lote: int,
    transfer_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    """
    Transfiere sobrantes de una orden a otra orden del mismo código.
    
    Body esperado:
    {
        "target_lote": int,
        "transfer_quantity": int
    }
    """
    target_lote = transfer_data.get("target_lote")
    transfer_quantity = transfer_data.get("transfer_quantity")
    
    if not target_lote or not transfer_quantity or transfer_quantity <= 0:
        raise HTTPException(status_code=400, detail="target_lote y transfer_quantity son requeridos y deben ser positivos")
    
    # Obtener orden origen (con sobrantes)
    source_order = db.query(order_model.Order).filter(order_model.Order.lote == source_lote).first()
    if not source_order:
        raise HTTPException(status_code=404, detail="Orden origen no encontrada")
    
    if source_order.missing_quantity >= 0:
        raise HTTPException(status_code=400, detail="La orden origen no tiene sobrantes para transferir")

    # La orden origen debe estar completada para poder ceder sobrantes (no cambiar su estado)
    if source_order.status != OrderStatus.completed:
        raise HTTPException(status_code=400, detail="La orden origen debe estar en estado 'completed' para transferir sobrantes")
    
    # Obtener orden destino
    target_order = db.query(order_model.Order).filter(order_model.Order.lote == target_lote).first()
    if not target_order:
        raise HTTPException(status_code=404, detail="Orden destino no encontrada")
    
    # Verificar que sean del mismo código
    if source_order.code != target_order.code:
        raise HTTPException(status_code=400, detail="Las órdenes deben tener el mismo código para transferir sobrantes")
    
    # Verificar que la cantidad a transferir no exceda los sobrantes disponibles
    available_surplus = abs(source_order.missing_quantity)
    if transfer_quantity > available_surplus:
        raise HTTPException(status_code=400, detail=f"No se pueden transferir {transfer_quantity} unidades. Solo hay {available_surplus} sobrantes disponibles")
    
    # Realizar la transferencia
    # Actualizar orden origen: reducir sobrantes
    source_order.missing_quantity += transfer_quantity  # Suma porque missing_quantity es negativo

    # Actualizar orden destino: la transferencia representa unidades recibidas en el lote destino.
    # Incrementamos received_quantity y recalculamos missing_quantity = quantity - received_quantity.
    target_order.received_quantity = (target_order.received_quantity or 0) + transfer_quantity
    target_order.missing_quantity = (target_order.quantity or 0) - target_order.received_quantity
    
    # No cambiamos el estado de la orden origen: la transferencia no debe alterar su estado
    
    db.commit()
    db.refresh(source_order)
    db.refresh(target_order)
    
    return {
        "message": f"Transferidos {transfer_quantity} unidades del lote {source_lote} al lote {target_lote}",
        "source_order": {
            "lote": source_order.lote,
            "remaining_surplus": abs(source_order.missing_quantity) if source_order.missing_quantity < 0 else 0,
            "status": source_order.status
        },
        "target_order": {
            "lote": target_order.lote,
            "received_quantity": target_order.received_quantity,
            "missing_quantity": target_order.missing_quantity,
            "status": target_order.status
        }
    }

@router.post("/{order_id}/receive")
def receive_order(
    order_id: str,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    """
    Recibe una orden entregada y la marca como completada.
    Proceso simplificado sin entrada de cantidad - confirmación automática.
    """
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if db_order.status != OrderStatus.delivered:
        raise HTTPException(status_code=400, detail="Solo se pueden recibir órdenes en estado 'delivered'")
    
    # Marcar como recibida y establecer fecha/usuario
    db_order.received_user = current_user.username
    db_order.received_date = datetime.now()

    # Determinar estado final: respetar custom_status si viene en body,
    # de lo contrario inferir según missing_quantity (pending si >0, completed si <=0)
    custom_status = body.get("custom_status") if isinstance(body, dict) else None
    if custom_status:
        if custom_status == "pending":
            db_order.status = OrderStatus.pending
            status_message = "pendiente (requiere revisión)"
        else:
            db_order.status = OrderStatus.completed
            status_message = "completada"
    else:
        try:
            current_missing = db_order.missing_quantity if db_order.missing_quantity is not None else 0
            if current_missing > 0:
                db_order.status = OrderStatus.pending
                status_message = "pendiente (quedan faltantes)"
            else:
                db_order.status = OrderStatus.completed
                status_message = "completada"
        except Exception:
            db_order.status = OrderStatus.completed
            status_message = "completada"
    db_order.status = OrderStatus.completed
    
    db.commit()
    db.refresh(db_order)
    
    return {
        "message": "Orden recibida y completada exitosamente",
        "lote": db_order.lote,
        "status": db_order.status,
        "received_user": db_order.received_user,
        "received_date": db_order.received_date
    }