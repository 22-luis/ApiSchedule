"""
Rutas de la API para la gestión de órdenes de producción: creación, actualización de estado, eliminación y consulta con filtros.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
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

router = APIRouter(prefix="/orders", tags=["orders"])

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
    
    # Serializar las órdenes creadas usando el esquema OrderOut
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
    return serialized_orders

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
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
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