from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.codes.models.code_automation_rule import CodeAutomationRule
from app.modules.codes.schemas.code_automation_rule import AutomationRuleCreate, AutomationRuleUpdate

class CodeAutomationRuleService:

    @staticmethod
    def create_rule(db: Session, code_id: UUID, rule_data: AutomationRuleCreate) -> CodeAutomationRule:
        db_rule = CodeAutomationRule(
            code_id=code_id,
            **rule_data.model_dump()
        )
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        return db_rule

    @staticmethod
    def get_rules_by_code(db: Session, code_id: UUID) -> List[CodeAutomationRule]:
        return db.query(CodeAutomationRule).filter(
            CodeAutomationRule.code_id == code_id
        ).order_by(CodeAutomationRule.priority.asc()).all()

    @staticmethod
    def get_rule(db: Session, rule_id: UUID) -> Optional[CodeAutomationRule]:
        return db.query(CodeAutomationRule).filter(CodeAutomationRule.id == rule_id).first()

    @staticmethod
    def update_rule(db: Session, rule_id: UUID, update_data: AutomationRuleUpdate) -> CodeAutomationRule:
        db_rule = CodeAutomationRuleService.get_rule(db, rule_id)
        if not db_rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_rule, key, value)
            
        db.commit()
        db.refresh(db_rule)
        return db_rule

    @staticmethod
    def delete_rule(db: Session, rule_id: UUID) -> bool:
        db_rule = CodeAutomationRuleService.get_rule(db, rule_id)
        if not db_rule:
            raise HTTPException(status_code=404, detail="Rule not found")
            
        db.delete(db_rule)
        db.commit()
        return True
