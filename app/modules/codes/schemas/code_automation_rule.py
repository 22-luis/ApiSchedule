from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class AutomationRuleBase(BaseModel):
    service_type: str = Field(..., description="Service type (FABRICATION, PACKAGING, WEIGHING)")
    activity_type: Optional[str] = Field(None, description="Specific activity type, e.g., M1, M5")
    priority: int = Field(1, description="Evaluation priority")
    min_quantity: Optional[float] = Field(None, description="Minimum quantity to match")
    max_quantity: Optional[float] = Field(None, description="Maximum quantity to match")
    target_team_id: UUID = Field(..., description="Target team ID")
    overflow_team_id: Optional[UUID] = Field(None, description="Overflow team ID")

class AutomationRuleCreate(AutomationRuleBase):
    pass

class AutomationRuleUpdate(BaseModel):
    service_type: Optional[str] = None
    activity_type: Optional[str] = None
    priority: Optional[int] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    target_team_id: Optional[UUID] = None
    overflow_team_id: Optional[UUID] = None

class AutomationRuleResponse(AutomationRuleBase):
    id: UUID
    code_id: UUID

    class Config:
        from_attributes = True
