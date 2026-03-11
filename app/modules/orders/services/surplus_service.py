from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from app.modules.orders.repositories import surplus_repository
from app.modules.orders.repositories import order_repository
from app.modules.orders.schemas.order_surplus import OrderSurplusCreate
from app.modules.orders.models.order_surplus import OrderSurplus

def get_all(db: Session) -> List[OrderSurplus]:
    """Obtiene todos los sobrantes."""
    return surplus_repository.find_all(db)

def get_by_lote(db: Session, lote: int) -> List[OrderSurplus]:
    """Obtiene sobrantes por lote."""
    return surplus_repository.find_by_lote(db, lote)

def create_surplus(db: Session, surplus_data: OrderSurplusCreate) -> OrderSurplus:
    """Crea un registro de sobrante individual."""
    new_surplus = OrderSurplus(**surplus_data.model_dump())
    return surplus_repository.save(db, new_surplus)

def create_surplus_batch(db: Session, surplus_list: List[OrderSurplusCreate]) -> dict:
    """Crea un lote de sobrantes y oculta las órdenes correspondientes."""
    try:
        for surplus_data in surplus_list:
            new_surplus = OrderSurplus(**surplus_data.model_dump())
            db.add(new_surplus)
            
            # Ocultar la orden correspondiente
            db_order = order_repository.find_by_lote(db, surplus_data.lote)
            if db_order:
                db_order.is_hidden = True
                db_order.hidden_at = datetime.now()
        
        db.commit()
        return {"message": f"Successfully processed {len(surplus_list)} surplus orders"}
    except Exception:
        db.rollback()
        raise
