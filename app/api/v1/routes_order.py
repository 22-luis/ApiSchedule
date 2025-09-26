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
from sqlalchemy import or_, and_
from app.core.task_config import (
    extract_created_orders_data, 
    get_orders_summary
)
from app.services.factory import TaskServiceFactory
from app.utils.order_status_service import OrderStatusService
from app.models.programming import ProgrammingTask
from datetime import date


def _get_delivery_status_message(status: OrderStatus, missing_quantity: int) -> str:
    if status == OrderStatus.completed:
        if missing_quantity < 0:
            return f"Orden completada con {abs(missing_quantity)} unidades adicionales."
        else:
            return "Orden completada."
    else:
        return f"Cantidad faltante: {missing_quantity}"

router = APIRouter(prefix="/orders", tags=["orders"])

def get_task_services():
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
            continue 
        
        # Limpiar los datos de la orden
        order_dict = order.dict()
        cleaned_order = clean_order_data(order_dict)
        
        initial_status = OrderStatus.unprogrammed
        
        #Not programable condition
        if order.bin not in [8,10]:
            initial_status = OrderStatus.not_programmable
        
        db_order = order_model.Order(
            lote=order.lote,
            dueDate=order.dueDate,
            code=cleaned_order['code'],
            description=cleaned_order['description'],
            quantity=order.quantity,
            missing_quantity=order.quantity,
            bin=order.bin,
            status=initial_status
        )
        db.add(db_order)
        created_orders.append(db_order)
    db.commit()
    for db_order in created_orders:
        db.refresh(db_order)
    
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
        
        # Obtener instancias de servicios usando el factory
        weighing_service, fabrication_service = get_task_services()
        
        # Crear instancia del servicio de empaque
        
        packaging_service = TaskServiceFactory.create_packaging_service()
        
        activities_data = weighing_service.get_activities_for_orders(extracted_orders, db)
        
        #La creacion automatica puede cambiar de como esta ahorita
        
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
def update_order_status(order_id: str, status_update: OrderStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))):
    
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

@router.post("/sync-status")
def sync_order_status(
    order_ids: Optional[List[int]] = Body(None, description="Lista de lotes de las órdenes a sincronizar. Si es nulo, se sincronizan todas."),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    if order_ids:
        orders = db.query(order_model.Order).filter(order_model.Order.lote.in_(order_ids)).all()
        if not orders:
            raise HTTPException(status_code=404, detail="No se encontraron órdenes con los lotes especificados")
    else:
        orders = db.query(order_model.Order).all()

    synced_count = 0
    for order in orders:
        try:
            OrderStatusService.sync_order_status_for_lote(db, str(order.lote))
            synced_count += 1
        except Exception as e:
            # Log the error for debugging, but continue with other orders
            print(f"Error syncing order {order.lote}: {str(e)}")
            continue
    
    return {
        "message": f"Synced {synced_count} out of {len(orders)} orders",
        "synced_count": synced_count,
        "total_orders": len(orders)
    }


@router.get("/", response_model=OrderPageOut)
def get_orders(
    status: Optional[List[str]] = Query(None, description="Filtrar por uno o más estados"),
    lote: int = Query(None, description="Filtrar por lote"),
    code: str = Query(None, description="Filtrar por código"),
    has_surplus: Optional[bool] = Query(None, description="Filtrar órdenes con sobrantes (missing_quantity < 0)"),
    bin_number: Optional[int] = Query(None, description="Filtrar por número de bin"),
    skip: int = Query(0, ge=0, description="Cuántos registros omitir (paginación)"),
    limit: int = Query(10, ge=1, le=1000, description="Cuántos registros devolver (paginación)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))
):
    
    query = db.query(order_model.Order)
    if status:
        query = query.filter(order_model.Order.status.in_(status))
    if lote:
        query = query.filter(order_model.Order.lote == lote)
    if code:
        query = query.filter(order_model.Order.code == code)
    if has_surplus is True:
        query = query.filter(order_model.Order.missing_quantity < 0)
    if bin_number is not None:
        query = query.filter(order_model.Order.bin == bin_number)

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
            "submitted_date": order.submitted_date,
            "submitted_observations": order.submitted_observations
        }
        serialized_orders.append(order_dict)
    
    return {"orders": serialized_orders, "total": total}

@router.post("/extract-orders-data")
def extract_orders_data(
    order_ids: Optional[List[int]] = Body(None),
    recent: bool = Body(False),
    limit: int = Body(10),
    status: Optional[OrderStatus] = Body(None),
    with_activities: bool = Body(False),
    with_weighing_activities: bool = Body(False),
    with_details: bool = Body(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    from app.core.task_config import extract_created_orders_data, get_orders_summary

    query = db.query(order_model.Order)

    if order_ids:
        query = query.filter(order_model.Order.lote.in_(order_ids))
    elif recent:
        if status:
            query = query.filter(order_model.Order.status == status)
        query = query.order_by(order_model.Order.lote.desc()).limit(limit)
    
    orders = query.all()

    if not orders:
        raise HTTPException(status_code=404, detail="No orders found with the specified criteria")

    extracted_orders = extract_created_orders_data(orders)
    summary = get_orders_summary(orders)
    
    response_data = {
        "extracted_orders": extracted_orders,
        "summary": summary,
    }

    if with_activities or with_weighing_activities:
        weighing_service, _ = get_task_services()
        activities_data = weighing_service.get_activities_for_orders(extracted_orders, db)
        
        if with_weighing_activities:
            weighing_activities = weighing_service.filter_activities(activities_data)
            response_data["weighing_activities_data"] = weighing_activities
            if with_details:
                weighing_activities_with_details = {}
                weighing_activities_by_code = weighing_activities.get("weighing_activities_by_code", {})
                for code, code_data in weighing_activities_by_code.items():
                    activities_with_details = []
                    for activity_data in code_data.get("weighing_activities", []):
                        activity_name = activity_data.get("activity")
                        if activity_name:
                            activity_details = weighing_service.get_activity_details_by_code_and_activity(code, activity_name, db)
                            activities_with_details.append({
                                "activity_data": activity_data,
                                "activity_details": activity_details
                            })
                    if activities_with_details:
                        weighing_activities_with_details[code] = {
                            "code": code,
                            "weighing_activities_with_details": activities_with_details
                        }
                response_data["weighing_activities_with_details_data"] = weighing_activities_with_details
        else:
            response_data["activities_data"] = activities_data

    return response_data


@router.post("/{order_id}/receive")
def receive_order(
    order_id: str,
    request_data: dict = Body(default={}),
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Previous verifications
    if db_order.status != OrderStatus.delivered:
        raise HTTPException(status_code=400, detail="La orden debe estar en estado 'entregado' para poder ser recibida")

    if db_order.status == OrderStatus.completed:
        raise HTTPException(status_code=400, detail="La orden ya está completada")
    
    # Mark as received and update fields
    db_order.received_user = current_user.username
    db_order.received_date = date.today()

    custom_status = request_data.get("custom_status")
    if custom_status:
        if custom_status == "pending":
            db_order.status = OrderStatus.pending
            status_message = "Pendiente"
        else:
            db_order.status = OrderStatus.completed
            status_message = "Completada"
    else:
        # Based on missing_quantity
        try:
            current_missing = db_order.missing_quantity if db_order.missing_quantity is not None else 0
            if current_missing > 0:
                db_order.status = OrderStatus.pending
                status_message = "pendiente (quedan faltantes)"
            else:
                db_order.status = OrderStatus.completed
                status_message = "completada"
        except Exception:
            # Fallback by default
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

@router.post("/{order_id}/deliver")
def deliver_order(
    order_id: str,
    delivery_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if db_order.status not in [OrderStatus.manufactured, OrderStatus.pending]:
        raise HTTPException(status_code=400, detail="Order must be in manufactured or pending status to be delivered")
    
    delivered_quantity = delivery_data.get("delivered_quantity")
    if delivered_quantity is None or delivered_quantity < 0:
        # Allow 0 delivered (explicit), but reject negative or missing values
        raise HTTPException(status_code=400, detail="Delivered quantity must be >= 0")
    
    submitted_observations = delivery_data.get("submitted_observations")

    # Calcular cantidad recibida total y faltante
    current_received = db_order.received_quantity or 0
    new_received_total = current_received + delivered_quantity
    new_missing_quantity = db_order.quantity - new_received_total
    
    # Actualizar campos de entrega
    db_order.submitted_user = current_user.username
    db_order.submitted_date = date.today()
    db_order.submitted_observations = submitted_observations
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
        "submitted_observations": db_order.submitted_observations,
        "message": f"Entrega realizada exitosamente. {_get_delivery_status_message(db_order.status, db_order.missing_quantity)}"
    }

@router.post("/get-activity-details")
def get_activity_details_for_code_and_activity(
    request: dict = Body(..., description="Código y actividad para obtener detalles"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    try:
        code = request.get("code")
        activity = request.get("activity")
        
        if not code or not activity:
            raise HTTPException(status_code=400, detail="Se requiere código y actividad")
        
        weighing_service, _ = get_task_services()
        # Obtener detalles de la actividad específica
        activity_details = weighing_service.get_activity_details_by_code_and_activity(code, activity, db)
        
        response_data = {
            "request": {"code": code, "activity": activity},
            "result": activity_details,
            "message": f"Detalles obtenidos para código '{code}' y actividad '{activity}'"
        }
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo detalles de actividad: {str(e)}")

@router.post("/calculate-minutes")
def calculate_minutes_for_activity(
    request: dict = Body(..., description="Datos para calcular minutos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    try:
        code = request.get("code")
        activity = request.get("activity")
        order_quantity = request.get("order_quantity")
        
        if not code or not activity or order_quantity is None:
            raise HTTPException(status_code=400, detail="Se requiere código, actividad y cantidad de la orden")
        
        weighing_service, _ = get_task_services()
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
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando minutos: {str(e)}")


@router.post("/weighing/find-suitable-programming")
def find_suitable_programming(
    task_minutes: int = Body(..., description="Minutos de la tarea para verificar límite de tiempo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    try:
        weighing_service, _ = get_task_services()
        team_result = weighing_service.get_most_suitable_weighing_team(db)
        
        if not team_result.get("success", False):
            raise HTTPException(status_code=404, detail="No se pudo obtener equipo idóneo para pesado")

        team_id = team_result.get("most_suitable_team", {}).get("id")
        available_programmings = weighing_service.get_available_programmings_for_team(team_id, db)
        
        if not available_programmings:
            time_verification = {"success": False, "message": "No hay programaciones disponibles para verificar"}
        else:
            time_verification = weighing_service.verify_programming_time_limit(available_programmings, task_minutes, db)
            
        return {
            "team_data": team_result,
            "available_programmings": {
                "programmings": available_programmings,
                "total_available_programmings": len(available_programmings)
            },
            "time_verification": time_verification
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo equipo con verificación de tiempo: {str(e)}")


@router.get("/available-for-transfer/{code}")
def get_available_orders_for_transfer(
    code: str,
    exclude_lote: Optional[int] = Query(None, description="Lote a excluir de los resultados"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
): 
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
