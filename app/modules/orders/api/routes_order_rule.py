from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.shared.db.session import get_db
from app.shared.utils.core.dependencies import require_roles
from app.modules.organization.models.role import UserRole
from app.modules.organization.models.user import User
from app.modules.orders.schemas.order_rule import OrderRule, OrderRuleCreate, OrderRuleUpdate
from app.modules.orders.services.order_rule_service import OrderRuleService

router = APIRouter(prefix="/orders/special-codes", tags=["orders"])

@router.get("/", response_model=List[OrderRule])
def get_order_rules(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER, UserRole.SUPERVISOR))
):
    return OrderRuleService.get_all(db, skip=skip, limit=limit, search=search)

@router.post("/", response_model=OrderRule)
def create_order_rule(
    order_rule_in: OrderRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    return OrderRuleService.create(db, order_rule_in)

@router.put("/{order_rule_id}", response_model=OrderRule)
def update_order_rule(
    order_rule_id: str,
    order_rule_in: OrderRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    return OrderRuleService.update(db, order_rule_id, order_rule_in)

@router.delete("/{order_rule_id}")
def delete_order_rule(
    order_rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.PLANNER))
):
    OrderRuleService.delete(db, order_rule_id)
    return {"message": "Excepción eliminada correctamente"}
