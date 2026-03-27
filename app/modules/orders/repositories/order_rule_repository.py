from typing import List, Optional
from sqlalchemy.orm import Session
from app.modules.orders.models.order_rule import OrderRule

def find_by_id(db: Session, order_rule_id: str) -> Optional[OrderRule]:
    return db.query(OrderRule).filter(OrderRule.id == order_rule_id).first()

def find_by_code(db: Session, code: str) -> Optional[OrderRule]:
    return db.query(OrderRule).filter(OrderRule.code == code).first()

def find_all(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[OrderRule]:
    query = db.query(OrderRule)
    if search:
        query = query.filter(OrderRule.code.ilike(f"%{search}%"))
    return query.offset(skip).limit(limit).all()

def save(db: Session, order_rule: OrderRule) -> OrderRule:
    db.add(order_rule)
    db.commit()
    db.refresh(order_rule)
    return order_rule

def delete(db: Session, order_rule: OrderRule) -> None:
    db.delete(order_rule)
    db.commit()
