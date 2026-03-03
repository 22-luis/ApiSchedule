from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
from app.modules.programming.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate, OrderPageOut, OrderWarehouseUpdate, OrderWarehouseOut, OrderDeliver
from app.modules.warehouse.models.history import WarehouseHistory, WarehouseHistoryType
from app.modules.programming.models import order as order_model
from app.shared.db.session import get_db
from typing import List, Union, Optional
from app.modules.core.models.user import User
from app.shared.utils.core.dependencies import get_current_user, require_roles
from app.modules.core.models.role import UserRole
from app.modules.programming.models.state import OrderStatus
from app.shared.utils.business.data_cleaning import clean_order_data
from datetime import datetime
from sqlalchemy import or_, and_
from app.modules.automation.services.task_config import (
    extract_created_orders_data, 
    get_orders_summary
)
from app.modules.automation.services.factory import TaskServiceFactory
from app.modules.automation.services.auto import create_tasks_for_lotes
from app.shared.utils.business.order_status_service import OrderStatusService
from app.modules.programming.models.programming import ProgrammingTask
from datetime import date
from app.shared.utils.core.logging import get_logger

logger = get_logger("routes_order")


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
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    logger.info(f"Received request to create orders. auto_create_tasks={auto_create_tasks}")
    
    # Si es una sola orden, la convertimos en lista
    if isinstance(orders, OrderCreate):
        orders = [orders]
    
    logger.debug(f"Processing {len(orders)} orders.")
    
    created_orders = []
    for order in orders:
        logger.debug(f"Processing order with lote: {order.lote}")
        
        # Verificar si la orden ya existe por el lote
        existing_order = db.query(order_model.Order).filter(order_model.Order.lote == order.lote).first()
        if existing_order:
            logger.info(f"Order with lote {order.lote} already exists. SKIPPING (not updating, not processing).")
            continue 
        
        # Limpiar los datos de la orden
        order_dict = order.dict()
        cleaned_order = clean_order_data(order_dict)
        
        initial_status = OrderStatus.unprogrammed
        
        #Not programable condition
        if order.bin not in [8, 10, 100]:
            initial_status = OrderStatus.not_programmable
            logger.info(f"Order with lote {order.lote} is not programmable (bin: {order.bin}). Setting status to {initial_status}.")
        
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
        logger.info(f"Order with lote {order.lote} marked for creation.")

    db.commit()
    logger.info(f"Committed {len(created_orders)} new orders to the database.")

    for db_order in created_orders:
        db.refresh(db_order)
    
    # Extraer solo lote, quantity y code de las órdenes creadas
    extracted_orders = extract_created_orders_data(created_orders)
    
    # Generar resumen simplificado
    summary = get_orders_summary(created_orders)
    
    # Serializar las órdenes creadas para la respuesta: normalizar tipos (str/int/float/ISO date)
    serialized_orders = []
    for order in created_orders:
        # Convertir status a cadena si es enum
        status_val = order.status.name if hasattr(order.status, 'name') else str(order.status)

        # Asegurar dueDate como string ISO (YYYY-MM-DD) si es date
        due_date_val = order.dueDate.isoformat() if hasattr(order.dueDate, 'isoformat') else order.dueDate

        order_dict = {
            "lote": int(order.lote) if order.lote is not None else None,
            "code": order.code,
            "status": status_val,
            "description": order.description,
            "quantity": float(order.quantity) if order.quantity is not None else 0.0,
            "bin": int(order.bin) if order.bin is not None else None,
            "dueDate": due_date_val
        }
        serialized_orders.append(order_dict)
    
    response_data = {
        "created_orders": serialized_orders,
        "extracted_orders": extracted_orders,
        "summary": summary,
        "auto_create_tasks": auto_create_tasks
    }
    
    # Separarórdenes de Bin 8 de las demás
    bin8_orders = [o for o in created_orders if o.bin == 8]
    other_orders = [o for o in created_orders if o.bin != 8]
    
    # Procesar órdenes Bin 8 sincrónicamente para capturar órdenes fallidas
    bin8_failed = []
    if bin8_orders:
        from app.modules.automation.services.order_flow_service import OrderFlowService
        
        logger.info(f"Processing {len(bin8_orders)} Bin 8 orders synchronously")
        bin_8_result = OrderFlowService.process_bin_8_orders(
            bin8_orders, 
            db, 
            fabrication_orders_in_batch=[o for o in created_orders if o.bin in [10, 100]]
        )
        
        processed_bin8 = bin_8_result["processed"]
        failed_bin8_raw = bin_8_result["failed"]
        # NEW: Self-sufficient orders (Bin 8 but treated as Bin 10 for task creation)
        self_sufficient_bin8 = bin_8_result.get("self_sufficient", [])
        
        # Add self-sufficient orders to other_orders so they get processed by create_tasks_for_lotes
        # This allows Weighing and Fabrication tasks to be created for them
        other_orders.extend(self_sufficient_bin8)
        
        # Crear tareas solo para las órdenes procesadas exitosamente
        if processed_bin8:
            logger.info(f"Creating tasks directly for {len(processed_bin8)} successfully processed Bin 8 orders")
            
            # Setup for direct task creation
            # Note: extract_created_orders_data and TaskServiceFactory are already imported globally

            
            # Prepare extracted orders with the CORRECT fabrication lot
            extracted_orders = extract_created_orders_data(processed_bin8)
            
            # Update lots with fabrication lots (which are available in current session)
            for i, extracted in enumerate(extracted_orders):
                original_order = processed_bin8[i]
                if hasattr(original_order, '_usar_lote_fabricacion'):
                    logger.info(
                        f"Using fabrication lote {original_order._usar_lote_fabricacion} "
                        f"instead of packaging lote {extracted['lote']} for task creation"
                    )
                    extracted['lote'] = original_order._usar_lote_fabricacion
                    extracted['original_packaging_lote'] = original_order._original_packaging_lote
                    extracted['bin'] = original_order.bin

            # Get packaging service and create tasks
            packaging_service = TaskServiceFactory.create_packaging_service()
            
            try:
                packaging_result = packaging_service.create_packaging_tasks_for_orders(
                    extracted_orders, db
                )
                logger.info(f"Synchronous task creation result: {packaging_result}")
                
                if packaging_result and packaging_result.get("tasks_created", 0) > 0:
                    # Commit task creation
                    db.commit()
                    
                    # --- Create notification for frontend banner ---
                    try:
                        created_tasks_info = packaging_result.get("created_tasks", [])
                        
                        from collections import defaultdict
                        prog_map = defaultdict(lambda: {"task_count": 0, "team_name": None, "programming_date": None})
                        
                        for task_info in created_tasks_info:
                            selected_prog = task_info.get("selected_programming")
                            if selected_prog:
                                prog_id = str(selected_prog.get("id"))
                                prog_map[prog_id]["task_count"] += 1
                                prog_map[prog_id]["team_name"] = selected_prog.get("team_name")
                                prog_date = selected_prog.get("date")
                                if hasattr(prog_date, 'strftime'):
                                    prog_date = prog_date.strftime('%Y-%m-%d')
                                prog_map[prog_id]["programming_date"] = str(prog_date)
                        
                        programming_info_list = [
                            {
                                "programming_id": prog_id,
                                "team_name": data["team_name"],
                                "programming_date": data["programming_date"],
                                "task_count": data["task_count"]
                            }
                            for prog_id, data in prog_map.items()
                        ]
                        
                        if programming_info_list:
                            from app.modules.programming.models.task_creation_notification import TaskCreationNotification
                            
                            notification = TaskCreationNotification(
                                created_by=current_user.username,
                                programming_info=programming_info_list,
                                order_count=len(processed_bin8)
                            )
                            db.add(notification)
                            db.commit()
                            logger.info(f"Created notification for automatic task creation: {len(programming_info_list)} programmings")
                    except Exception as notif_error:
                        logger.error(f"Error creating notification: {notif_error}")

            except Exception as e:
                logger.error(f"Error creating tasks synchronously: {e}")
                # Don't fail the whole request, but log error
                # Maybe add to failed list? For now just log.
        
        # Preparar información de órdenes fallidas para el frontend
        for failed_info in failed_bin8_raw:
            order = failed_info["order"]
            bin8_failed.append({
                "lote": int(order.lote),
                "code": order.code,
                "description": order.description,
                "quantity": float(order.quantity),
                "bin": int(order.bin),
                "dueDate": order.dueDate.isoformat() if hasattr(order.dueDate, 'isoformat') else order.dueDate,
                "fabrication_code": failed_info.get("fabrication_code"),
                "reason": failed_info["reason"]
            })
        
        if bin8_failed:
            logger.warning(f"{len(bin8_failed)} Bin 8 orders failed and require manual lot selection")
        
    # Solo crear tareas para otras órdenes si auto_create_tasks es True
    if auto_create_tasks and other_orders:
        other_lotes = [o.lote for o in other_orders]
        if background_tasks is not None:
            background_tasks.add_task(create_tasks_for_lotes, other_lotes, current_user.username)
            response_data.update({
                "task_creation_scheduled": True,
                "message": f"Se crearon {len(created_orders)} órdenes exitosamente. La creación de tareas se programó en background."
            })
        else:
            # Fallback: run inline (keeps previous behavior)
            create_tasks_for_lotes(other_lotes, current_user.username)
            response_data.update({
                "task_creation_scheduled": False,
                "message": f"Se crearon {len(created_orders)} órdenes exitosamente. Las tareas se crearon en el mismo proceso."
            })
    elif bin8_orders and not other_orders:
        # Solo había órdenes Bin 8
        processed_count = len(bin8_orders) - len(bin8_failed)
        message = f"Se crearon {len(bin8_orders)} órdenes de Bin 8."
        if processed_count > 0:
            message += f" {processed_count} tareas {'programadas' if background_tasks else 'creadas'} automáticamente."
        if bin8_failed:
            message += f" {len(bin8_failed)} órdenes requieren selección manual de lote."
        response_data.update({
            "task_creation_scheduled": background_tasks is not None,
            "message": message
        })
    else:
        logger.info("auto_create_tasks is False. Skipping task creation.")
        response_data.update({
            "message": f"Se crearon {len(created_orders)} órdenes exitosamente. No se crearon tareas automáticamente."
        })
    
    # Agregar información de órdenes bin 8 fallidas a la respuesta
    if bin8_failed:
        response_data["bin8_failed"] = bin8_failed
    
    logger.info("Finished processing create_orders request.")
    return response_data

@router.delete("/{order_id}")
def delete_order(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only delete the order - tasks are preserved (they will be orphaned but keep their programming)
    db.delete(db_order)
    db.commit()
    return {"message": "Order deleted successfully. Tasks were preserved."}

@router.post("/{order_lote}/create_tasks_manual")
def create_tasks_for_bin8_manual(
    order_lote: int,
    request_data: dict = Body(..., description="Objeto con fabrication_lote"),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    """
    Manually create tasks for a bin 8 order with a specified fabrication lot.
    This is used when automatic matching fails and the user needs to manually select the fabrication lot.
    """
    fabrication_lote = request_data.get("fabrication_lote")
    if not fabrication_lote:
        raise HTTPException(status_code=400, detail="fabrication_lote is required")

    
    logger.info(f"Manual task creation requested for order {order_lote} with fabrication lot {fabrication_lote}")
    
    # Obtener la orden de empaque
    packaging_order = db.query(order_model.Order).filter(
        order_model.Order.lote == order_lote
    ).first()
    
    if not packaging_order:
        raise HTTPException(status_code=404, detail=f"Order {order_lote} not found")
    
    if packaging_order.bin != 8:
        raise HTTPException(status_code=400, detail=f"Order {order_lote} is not a bin 8 (packaging) order")
    
    # Verificar que la orden no esté ya programada
    if packaging_order.status not in [OrderStatus.unprogrammed]:
        logger.warning(f"Order {order_lote} is already in status {packaging_order.status}")
        # Permitir re-procesar si es necesario, pero advertir
    
    # Verificar que el lote de fabricación existe
    fabrication_order = db.query(order_model.Order).filter(
        order_model.Order.lote == fabrication_lote
    ).first()
    
    if not fabrication_order:
        raise HTTPException(status_code=404, detail=f"Fabrication lot {fabrication_lote} not found")
    
    # Cambiar estado de la orden
    packaging_order.status = OrderStatus.programmed
    db.commit()
    
    logger.info(f"Order {order_lote} linked to fabrication lot {fabrication_lote} manually")
    
    # Crear tareas directamente usando el lote de fabricación especificado
    # No usamos attributes temporales, en su lugar creamos las tareas directamente
    from app.modules.automation.services.task_config import extract_created_orders_data
    from app.modules.automation.services.factory import TaskServiceFactory
    
    # Extract order data but replace lote with fabrication lote
    extracted = {
        "lote": fabrication_lote,  # Use fabrication lot for task creation
        "code": packaging_order.code,
        "quantity": packaging_order.quantity,
        "bin": packaging_order.bin,
        "original_packaging_lote": order_lote  # Track original for reference
    }
    
    logger.info(f"Creating tasks with extracted data: {extracted}")
    
    # Get packaging service and create tasks
    packaging_service = TaskServiceFactory.create_packaging_service()
    
    try:
        result = packaging_service.create_packaging_tasks_for_orders([extracted], db)
        logger.info(f"Task creation result: {result}")
        
        if result and result.get("tasks_created", 0) > 0:
            db.commit()
            message = f"Se crearon {result.get('tasks_created', 0)} tareas para orden {order_lote} usando lote de fabricación {fabrication_lote}"
            
            # --- Crear notificación para el banner del frontend ---
            try:
                # Extraer información de programación de las tareas creadas
                created_tasks_info = result.get("created_tasks", [])
                programming_info_list = []
                
                # Agrupar por programming_id para evitar duplicados si se crearon múltiples tareas en la misma programación
                # (aunque para una sola orden usualmente es una programación, pero por si acaso)
                from collections import defaultdict
                prog_map = defaultdict(lambda: {"task_count": 0, "team_name": None, "programming_date": None})
                
                for task_info in created_tasks_info:
                    selected_prog = task_info.get("selected_programming")
                    if selected_prog:
                        prog_id = str(selected_prog.get("id"))
                        prog_map[prog_id]["task_count"] += 1
                        prog_map[prog_id]["team_name"] = selected_prog.get("team_name")
                        # Asegurar formato de fecha string YYYY-MM-DD
                        prog_date = selected_prog.get("date")
                        if hasattr(prog_date, 'strftime'):
                            prog_date = prog_date.strftime('%Y-%m-%d')
                        prog_map[prog_id]["programming_date"] = str(prog_date)
                
                # Convertir a lista formato para el modelo
                programming_info_list = [
                    {
                        "programming_id": prog_id,
                        "team_name": data["team_name"],
                        "programming_date": data["programming_date"],
                        "task_count": data["task_count"]
                    }
                    for prog_id, data in prog_map.items()
                ]
                
                if programming_info_list:
                    from app.modules.programming.models.task_creation_notification import TaskCreationNotification
                    
                    notification = TaskCreationNotification(
                        created_by=current_user.username,
                        programming_info=programming_info_list,
                        order_count=1 # Estamos procesando solo 1 orden manualmente aquí
                    )
                    db.add(notification)
                    db.commit()
                    logger.info(f"Created notification for manual task creation: {len(programming_info_list)} programmings")
            except Exception as notif_error:
                logger.error(f"Error creating notification: {notif_error}")
                # No fallamos el request principal si falla la notificación, solo logueamos

        else:
            message = f"No se crearon tareas para orden {order_lote}. Verifica los logs del servidor."
    except Exception as e:
        logger.error(f"Error creating tasks for order {order_lote}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creando tareas: {str(e)}")
    
    return {
        "success": True,
        "message": message,
        "order_lote": order_lote,
        "fabrication_lote": fabrication_lote,
        "tasks_created": result.get("tasks_created", 0) if result else 0
    }

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
    is_hidden: Optional[bool] = Query(None, description="Filtrar por visibilidad (is_hidden)"),
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
    if is_hidden is not None:
        if is_hidden is False:
            query = query.filter(or_(order_model.Order.is_hidden == False, order_model.Order.is_hidden == None))
        else:
            query = query.filter(order_model.Order.is_hidden == is_hidden)

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
            "submitted_observations": order.submitted_observations,
            "is_hidden": order.is_hidden
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
    from app.modules.automation.services.task_config import extract_created_orders_data, get_orders_summary

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
    if db_order.status not in [OrderStatus.delivered, OrderStatus.not_programmable]:
        raise HTTPException(status_code=400, detail="La orden debe estar en estado 'entregado' o 'no programable' para poder ser recibida")

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

    # Record history
    history = WarehouseHistory(
        lote=db_order.lote,
        code=db_order.code,
        quantity=db_order.received_quantity if db_order.received_quantity is not None else 0,
        type=WarehouseHistoryType.RECEIVED,
        user=current_user.username,
        observations=f"Orden recibida. Estado: {status_message}"
    )
    db.add(history)
    
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
    order_id: int,
    delivery_data: OrderDeliver,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    delivered_quantity = delivery_data.delivered_quantity
    submitted_observations = delivery_data.submitted_observations

    # Actualizar campos de entrega
    db_order.submitted_user = current_user.username
    db_order.submitted_date = date.today()
    db_order.submitted_observations = submitted_observations
    
    # Update quantities
    # received_quantity tracks total delivered so far
    current_received = db_order.received_quantity if db_order.received_quantity is not None else 0
    new_received_total = current_received + delivered_quantity
    db_order.received_quantity = new_received_total
    
    # Calculate new missing quantity
    # missing_quantity = quantity - received_quantity
    # If quantity is 100 and we received 40, missing is 60.
    # If we deliver 40 more, new_received is 80, missing becomes 20.
    if db_order.quantity is not None:
        new_missing_quantity = db_order.quantity - new_received_total
        db_order.missing_quantity = new_missing_quantity
    else:
        # Fallback if quantity is somehow None, though schema prevents it usually
        new_missing_quantity = -new_received_total
        db_order.missing_quantity = new_missing_quantity

    
    # Cambiar estado a delivered (independientemente de la cantidad)
    # El estado solo cambiará a completed cuando se reciba en almacén
    db_order.status = OrderStatus.delivered
    
    # Record history
    history = WarehouseHistory(
        lote=db_order.lote,
        code=db_order.code,
        quantity=delivered_quantity,
        type=WarehouseHistoryType.SENT,
        user=current_user.username,
        observations=submitted_observations
    )
    db.add(history)
    
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
    
    # Record history for source
    history_source = WarehouseHistory(
        lote=source_order.lote,
        code=source_order.code,
        quantity=transfer_quantity,
        type=WarehouseHistoryType.TRANSFER_SOURCE,
        user=current_user.username,
        observations=f"Sobrante transferido al lote {target_order.lote}"
    )
    db.add(history_source)

    # Record history for target
    history_target = WarehouseHistory(
        lote=target_order.lote,
        code=target_order.code,
        quantity=transfer_quantity,
        type=WarehouseHistoryType.TRANSFER_TARGET,
        user=current_user.username,
        observations=f"Sobrante recibido del lote {source_order.lote}"
    )
    db.add(history_target)

    db.commit()
    db.refresh(source_order)
@router.patch("/{order_id}/hide")
def hide_order(
    order_id: int,
    is_hidden: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    db_order = db.query(order_model.Order).filter(order_model.Order.lote == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_order.is_hidden = is_hidden
    if is_hidden:
        db_order.hidden_at = datetime.now()
    else:
        db_order.hidden_at = None
    db.commit()
    db.refresh(db_order)
    
    return {"message": "Visibilidad de la orden actualizada", "is_hidden": db_order.is_hidden}
