"""
Rutas de la API para la gestión de órdenes de producción: creación, actualización de estado, eliminación y consulta con filtros.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate
from app.models import order as order_model
from app.db.dependency import get_db
from typing import List, Union, Optional
from app.schemas.order import OrderOut
from app.models.user import User
from app.utils.dependencies import get_current_user, require_roles
from app.models.role import UserRole
from app.schemas.order import OrderStatusUpdate
from app.models.state import OrderStatus

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
        db_order = order_model.Order(
            lote=order.lote,
            dueDate=order.dueDate,
            code=order.code,
            description=order.description,
            quantity=order.quantity,
            bin=order.bin,
            status=order.status,
        )
        db.add(db_order)
        created_orders.append(db_order)
    db.commit()
    for db_order in created_orders:
        db.refresh(db_order)
    return created_orders

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
    return db_order

@router.get("/", response_model=List[OrderOut])
def get_orders(
    status: Optional[OrderStatus] = Query(None, description="Filtrar por status"),
    lote: int = Query(None, description="Filtrar por lote"),
    code: str = Query(None, description="Filtrar por código"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PLANNER, UserRole.SUPERVISOR))
):
    query = db.query(order_model.Order)
    if status:
        query = query.filter(order_model.Order.status == status.value)
    if lote:
        query = query.filter(order_model.Order.lote == lote)
    if code:
        query = query.filter(order_model.Order.code == code)
    orders = query.all()
    return orders