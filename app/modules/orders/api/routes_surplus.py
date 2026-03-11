from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.orders.models.order_surplus import OrderSurplus
from app.modules.orders.models.order import Order
from app.modules.orders.schemas.order_surplus import OrderSurplusCreate, OrderSurplusOut

router = APIRouter(prefix="/surplus", tags=["surplus"])

@router.get("/", response_model=List[OrderSurplusOut])
def get_surpluses(
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    return db.query(OrderSurplus).all()

@router.post("/", response_model=OrderSurplusOut, status_code=201)
def create_surplus(
    surplus_data: OrderSurplusCreate,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    new_surplus = OrderSurplus(**surplus_data.model_dump())
    db.add(new_surplus)
    db.commit()
    db.refresh(new_surplus)
    return new_surplus

from datetime import datetime
@router.post("/batch", status_code=201)
def create_surplus_batch(
    surplus_list: List[OrderSurplusCreate],
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    try:
        # Create all surplus records
        for surplus_data in surplus_list:
            new_surplus = OrderSurplus(**surplus_data.model_dump())
            db.add(new_surplus)
            
            # Hide the corresponding order and set hidden_at
            db.query(Order).filter(Order.lote == surplus_data.lote).update({
                "is_hidden": True,
                "hidden_at": datetime.now()
            })
        
        db.commit()
        return {"message": f"Successfully processed {len(surplus_list)} surplus orders"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lote}", response_model=List[OrderSurplusOut])
def get_surplus_by_lote(
    lote: int,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    return db.query(OrderSurplus).filter(OrderSurplus.lote == lote).all()
