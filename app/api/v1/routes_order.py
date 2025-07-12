from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate
from app.models import order as order_model
from app.db.dependency import get_db
from typing import List
from app.schemas.order import OrderOut
from app.models.user import User
from app.utils.dependencies import get_current_user, require_roles
from app.models.role import UserRole

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/")
def create_order(order: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
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
    db.refresh(db_order)
    return db_order

@router.delete("/{order_id}")
def delete_order(order_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))):
    db_order = db.query(order_model.Order).filter(order_model.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(db_order)
    db.commit()
    return {"message": "Order deleted successfully"}

@router.get("/", response_model=List[OrderOut])
def get_orders(db: Session = Depends(get_db), current_user: User = Depends(require_roles(UserRole.PLANNER, UserRole.SUPERVISOR))):
    orders = db.query(order_model.Order).all()
    return orders
