from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Union, Optional
from datetime import datetime

from app.modules.orders.schemas.order import OrderCreate, OrderPageOut, OrderWarehouseUpdate, OrderDeliver, OrderStatusUpdate
from app.modules.organization.models.user import User
from app.modules.organization.models.role import UserRole
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles
from app.modules.orders.services.order_service import OrderService
from app.modules.orders.repositories import order_repository
from app.modules.automation.services.factory import TaskServiceFactory
from app.shared.utils.business.order_status_service import OrderStatusService
from app.shared.utils.core.logging import get_logger

logger = get_logger("routes_order")

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
    if isinstance(orders, OrderCreate):
        orders = [orders]
    return OrderService.create_orders(db, orders, auto_create_tasks, current_user, background_tasks)

@router.get("/", response_model=OrderPageOut)
def get_orders(
    status: Optional[List[str]] = Query(None),
    lote: int = Query(None),
    code: str = Query(None),
    has_surplus: Optional[bool] = Query(None),
    is_hidden: Optional[bool] = Query(None),
    bin_number: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))
):
    filters = {
        "status": status, "lote": lote, "code": code, "has_surplus": has_surplus,
        "is_hidden": is_hidden, "bin_number": bin_number, "skip": skip, "limit": limit
    }
    return OrderService.get_paged_orders(db, filters)

@router.delete("/{order_id}")
def delete_order(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_order = order_repository.find_by_lote(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    order_repository.delete(db, db_order)
    return {"message": "Order deleted successfully. Tasks were preserved."}

@router.patch("/{order_id}/status")
def update_order_status(order_id: str, status_update: OrderStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))):
    db_order = order_repository.find_by_lote(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_order.status = status_update.status
    db.commit()
    db.refresh(db_order)
    return {
        "lote": db_order.lote, "code": db_order.code, "status": db_order.status,
        "description": db_order.description, "quantity": db_order.quantity,
        "bin": db_order.bin, "dueDate": db_order.dueDate, "missing_quantity": db_order.missing_quantity
    }

@router.post("/{order_id}/receive")
def receive_order(
    order_id: str,
    request_data: dict = Body(default={}),
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    return OrderService.receive_order(db, order_id, request_data.get("custom_status"), current_user)

@router.post("/{order_id}/deliver")
def deliver_order(
    order_id: int,
    delivery_data: OrderDeliver,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return OrderService.deliver_order(db, order_id, delivery_data.delivered_quantity, delivery_data.submitted_observations, current_user)

@router.post("/{source_lote}/transfer-surplus")
def transfer_surplus_to_order(
    source_lote: int,
    transfer_data: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return OrderService.transfer_surplus(
        db, source_lote, transfer_data.get("target_lote"), 
        transfer_data.get("transfer_quantity"), current_user
    )

@router.patch("/{order_id}/hide")
def hide_order(
    order_id: int,
    is_hidden: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.WAREHOUSE))
):
    db_order = order_repository.find_by_lote(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    db_order.is_hidden = is_hidden
    db_order.hidden_at = datetime.now() if is_hidden else None
    db.commit()
    return {"message": "Visibilidad de la orden actualizada", "is_hidden": db_order.is_hidden}

# Otros endpoints simplificados... (manteniendo funciones de utilidad de automatización si es necesario)
@router.post("/sync-status")
def sync_order_status(
    order_ids: Optional[List[int]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    orders = db.query(Order).filter(Order.lote.in_(order_ids)).all() if order_ids else db.query(Order).all()
    synced_count = 0
    for order in orders:
        try:
            OrderStatusService.sync_order_status_for_lote(db, str(order.lote))
            synced_count += 1
        except Exception: continue
    return {"message": f"Synced {synced_count} out of {len(orders)} orders"}

@router.get("/available-for-transfer/{code}")
def get_available_orders_for_transfer(
    code: str,
    exclude_lote: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
): 
    code_base = code.split('-')[0].strip()
    available_orders = order_repository.find_by_code_prefix(db, code_base, exclude_lote)
    return {"available_orders": [
        {"lote": o.lote, "code": o.code, "status": o.status, "description": o.description,
         "quantity": o.quantity, "missing_quantity": o.missing_quantity, "dueDate": o.dueDate}
        for o in available_orders
    ]}
