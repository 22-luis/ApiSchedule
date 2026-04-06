from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.shared.db.session import get_db
from app.modules.codes.schemas.code_automation_rule import AutomationRuleCreate, AutomationRuleUpdate, AutomationRuleResponse
from app.modules.codes.services.code_automation_rule_service import CodeAutomationRuleService

router = APIRouter(prefix="/codes", tags=["Code Automation Rules"])

@router.post("/{code_id}/rules", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(code_id: UUID, rule_in: AutomationRuleCreate, db: Session = Depends(get_db)):
    """Create a new automation rule for a specfic code."""
    return CodeAutomationRuleService.create_rule(db, code_id, rule_in)

@router.get("/{code_id}/rules", response_model=List[AutomationRuleResponse])
def get_rules_by_code(code_id: UUID, db: Session = Depends(get_db)):
    """Get all automation rules for a specific code."""
    return CodeAutomationRuleService.get_rules_by_code(db, code_id)

@router.get("/rules/{rule_id}", response_model=AutomationRuleResponse)
def get_rule_by_id(rule_id: UUID, db: Session = Depends(get_db)):
    """Get a specific automation rule."""
    rule = CodeAutomationRuleService.get_rule(db, rule_id)
    if not rule:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.put("/rules/{rule_id}", response_model=AutomationRuleResponse)
def update_rule(rule_id: UUID, rule_in: AutomationRuleUpdate, db: Session = Depends(get_db)):
    """Update an automation rule."""
    return CodeAutomationRuleService.update_rule(db, rule_id, rule_in)

@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: UUID, db: Session = Depends(get_db)):
    """Delete an automation rule."""
    CodeAutomationRuleService.delete_rule(db, rule_id)
    return None
