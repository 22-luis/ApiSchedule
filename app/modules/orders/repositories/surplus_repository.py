from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.orders.models.order_surplus import OrderSurplus

def find_all(db: Session) -> List[OrderSurplus]:
    """Obtiene todos los registros de sobrantes."""
    return db.query(OrderSurplus).all()

def find_by_lote(db: Session, lote: int) -> List[OrderSurplus]:
    """Busca sobrantes por lote."""
    return db.query(OrderSurplus).filter(OrderSurplus.lote == lote).all()

def save(db: Session, surplus: OrderSurplus) -> OrderSurplus:
    """Guarda un registro de sobrante."""
    db.add(surplus)
    db.commit()
    db.refresh(surplus)
    return surplus
