from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import HTTPException
from app.modules.orders.models.order_rule import OrderRule
from app.modules.orders.repositories import order_rule_repository
from app.modules.orders.schemas.order_rule import OrderRuleCreate, OrderRuleUpdate

class OrderRuleService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[OrderRule]:
        return order_rule_repository.find_all(db, skip=skip, limit=limit, search=search)

    @staticmethod
    def create(db: Session, order_rule_in: OrderRuleCreate) -> OrderRule:
        existing = order_rule_repository.find_by_code(db, order_rule_in.code)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe una excepción para este código")
        
        db_obj = OrderRule(
            code=order_rule_in.code,
            programming_code=order_rule_in.programming_code
        )
        return order_rule_repository.save(db, db_obj)

    @staticmethod
    def update(db: Session, order_rule_id: str, order_rule_in: OrderRuleUpdate) -> OrderRule:
        db_obj = order_rule_repository.find_by_id(db, order_rule_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Excepción no encontrada")
        
        update_data = order_rule_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        return order_rule_repository.save(db, db_obj)

    @staticmethod
    def delete(db: Session, order_rule_id: str) -> None:
        db_obj = order_rule_repository.find_by_id(db, order_rule_id)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Excepción no encontrada")
        order_rule_repository.delete(db, db_obj)
