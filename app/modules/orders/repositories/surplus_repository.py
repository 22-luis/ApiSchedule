from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.orders.models.order_surplus import OrderSurplus

def find_all(db: Session) -> List[OrderSurplus]:
    return db.query(OrderSurplus).all()

def find_by_lote(db: Session, lote: int) -> List[OrderSurplus]:
    return db.query(OrderSurplus).filter(OrderSurplus.lote == lote).all()

def save(db: Session, surplus: OrderSurplus) -> OrderSurplus:
    db.add(surplus)
    db.commit()
    db.refresh(surplus)
    return surplus
