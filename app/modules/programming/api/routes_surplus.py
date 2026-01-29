from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.programming.models.order_surplus import OrderSurplus
from app.modules.programming.schemas.order_surplus import OrderSurplusCreate, OrderSurplusOut

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

@router.get("/{lote}", response_model=List[OrderSurplusOut])
def get_surplus_by_lote(
    lote: int,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    return db.query(OrderSurplus).filter(OrderSurplus.lote == lote).all()
