from pydantic import BaseModel, Extra, Field
from datetime import date, datetime
from typing import Dict, Any, List, Optional

class TaskDurationRequest(BaseModel):
    quantity: float = Field(..., gt=0, description="Cantidad a producir")
    productivity: float = Field(..., gt=0, description="Productividad")
    people: float = Field(..., gt=0, description="Número de personas")
    code_people: Optional[float] = Field(None, description="Personas requeridas por código")

class TaskDurationResponse(BaseModel):
    minutes: int
    hours: float
    formula_used: str

class WorkingHoursRequest(BaseModel):
    date: date

class WorkingHoursResponse(BaseModel):
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    is_working_day: bool
    total_hours: float

class TaskWithMinutes(BaseModel):
    minutes: int

    class Config:
        extra = Extra.allow 

class SequentialTimesRequest(BaseModel):
    base_date: date
    base_time: Optional[str] = None
    tasks: List[TaskWithMinutes]

class TaskFormValidationRequest(BaseModel):
    form_data: Dict[str, Any]

class ExtraTaskValidationRequest(BaseModel):
    description: str = Field(..., min_length=1)
    minutes: float = Field(..., gt=0)
    selected_team: str
    programming_id: str

class TaskEfficiencyRequest(BaseModel):
    planned_minutes: int
    actual_minutes: int

class TeamWorkloadRequest(BaseModel):
    tasks: List[Dict[str, Any]]
    working_hours: int = 8

class TimeFormatRequest(BaseModel):
    time_str: str
