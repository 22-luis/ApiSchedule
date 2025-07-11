from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.order import OrderCreate
from app.models import order as order_model
from app.db.dependency import get_db

router = APIRouter()

@router.post("/orders")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    db_order = order_model.Order(
        lot=order.lot,
        date=order.created_at,
        code=order.code,
        description=order.description,
        amount=order.amount,
        bin=order.bin,
        state=order.state,
    )
    db.add(db_order)
    db.refresh(db_order)
    return db_order