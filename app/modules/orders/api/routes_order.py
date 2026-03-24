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
from app.modules.automation.services.factory import TaskServiceFactory
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
    return OrderService.delete_order(db, order_id)

@router.patch("/{order_id}/status")
def update_order_status(order_id: str, status_update: OrderStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.WAREHOUSE, UserRole.USER))):
    return OrderService.update_order_status(db, order_id, status_update.status)

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
    return OrderService.hide_order(db, order_id, is_hidden)

# Otros endpoints simplificados... (manteniendo funciones de utilidad de automatización si es necesario)
@router.post("/sync-status")
def sync_order_status(
    order_ids: Optional[List[int]] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR, UserRole.USER))
):
    return OrderService.sync_order_statuses(db, order_ids)

@router.get("/available-for-transfer/{code}")
def get_available_orders_for_transfer(
    code: str,
    exclude_lote: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
): 
    return OrderService.get_available_orders_for_transfer(db, code, exclude_lote)
