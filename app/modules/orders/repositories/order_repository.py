from typing import List, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.modules.orders.models.order import Order
from app.modules.orders.models.state import OrderStatus

def find_by_lote(db: Session, lote: Union[int, str]) -> Optional[Order]:
    """Busca una orden por su lote."""
    return db.query(Order).filter(Order.lote == lote).first()

def find_all(
    db: Session,
    status: Optional[List[str]] = None,
    lote: Optional[int] = None,
    code: Optional[str] = None,
    has_surplus: Optional[bool] = None,
    bin_number: Optional[int] = None,
    is_hidden: Optional[bool] = None,
    skip: int = 0,
    limit: int = 10
) -> List[Order]:
    """Busca órdenes con filtros y paginación."""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status.in_(status))
    if lote:
        query = query.filter(Order.lote == lote)
    if code:
        query = query.filter(Order.code == code)
    if has_surplus is True:
        query = query.filter(Order.missing_quantity < 0)
    if bin_number is not None:
        query = query.filter(Order.bin == bin_number)
    if is_hidden is not None:
        if is_hidden is False:
            query = query.filter(or_(Order.is_hidden == False, Order.is_hidden == None))
        else:
            query = query.filter(Order.is_hidden == is_hidden)
            
    return query.offset(skip).limit(limit).all()

def count_all(
    db: Session,
    status: Optional[List[str]] = None,
    lote: Optional[int] = None,
    code: Optional[str] = None,
    has_surplus: Optional[bool] = None,
    bin_number: Optional[int] = None,
    is_hidden: Optional[bool] = None
) -> int:
    """Cuenta el total de órdenes que coinciden con los filtros."""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status.in_(status))
    if lote:
        query = query.filter(Order.lote == lote)
    if code:
        query = query.filter(Order.code == code)
    if has_surplus is True:
        query = query.filter(Order.missing_quantity < 0)
    if bin_number is not None:
        query = query.filter(Order.bin == bin_number)
    if is_hidden is not None:
        if is_hidden is False:
            query = query.filter(or_(Order.is_hidden == False, Order.is_hidden == None))
        else:
            query = query.filter(Order.is_hidden == is_hidden)
            
    return query.count()

def save(db: Session, order: Order) -> Order:
    """Guarda o actualiza una orden."""
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def delete(db: Session, order: Order) -> None:
    """Elimina una orden."""
    db.delete(order)
    db.commit()

def find_by_code_prefix(db: Session, code_prefix: str, exclude_lote: Optional[int] = None) -> List[Order]:
    """Busca órdenes por prefijo de código para transferencias."""
    query = db.query(Order).filter(
        Order.code.ilike(f"{code_prefix}%"),
        Order.status.in_([OrderStatus.unprogrammed, OrderStatus.programmed, OrderStatus.manufactured]),
        Order.missing_quantity >= 0
    )
    if exclude_lote:
        query = query.filter(Order.lote != exclude_lote)
    return query.all()
