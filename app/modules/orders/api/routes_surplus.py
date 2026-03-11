from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import get_current_user
from app.modules.orders.schemas.order_surplus import OrderSurplusCreate, OrderSurplusOut
from app.modules.orders.services import surplus_service

router = APIRouter(prefix="/surplus", tags=["surplus"])

@router.get("/", response_model=List[OrderSurplusOut])
def get_surpluses(
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    return surplus_service.get_all(db)

@router.post("/", response_model=OrderSurplusOut, status_code=201)
def create_surplus(
    surplus_data: OrderSurplusCreate,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    return surplus_service.create_surplus(db, surplus_data)

@router.post("/batch", status_code=201)
def create_surplus_batch(
    surplus_list: List[OrderSurplusCreate],
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    try:
        return surplus_service.create_surplus_batch(db, surplus_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lote}", response_model=List[OrderSurplusOut])
def get_surplus_by_lote(
    lote: int,
    db: Session = Depends(get_db),
    _current_user = Depends(get_current_user)
):
    return surplus_service.get_by_lote(db, lote)
